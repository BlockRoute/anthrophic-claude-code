"""GMGN OpenAPI adapter.

An alternative to the Blockscout source. GMGN returns trades already classified
as buy/sell and candles already aggregated, so this module skips hoodtrack's
transfer-reconstruction stage entirely and produces `Trade` and `PriceSeries`
objects directly.

Spec (verified against the gmgn-cli source, GMGNAI/gmgn-skills):

  base                https://openapi.gmgn.ai
  auth                X-APIKEY header, plus `timestamp` and `client_id` query
                      params on every request. Read endpoints need nothing more;
                      only swap/order/holdings require the signing private key.
  GET /v1/user/wallet_activity
                      chain, wallet_address, [token_address, limit, cursor, type]
                      -> {code, data: {activities: [...], next: <cursor>}}
  GET /v1/market/token_kline
                      chain, address, resolution, [from, to]
                      -> {code, data: {list: [{time, open, high, low, close,
                                               volume, amount, source}]}}

Two traps this module exists to absorb:

  * kline `time` is in MILLISECONDS while activity `timestamp` is in SECONDS.
    Mixing them silently puts every price 50,000 years after every trade.
  * every kline numeric arrives as a JSON *string* ("close": "0.0000082444906").

UNITS: GMGN denominates in USD, not ETH. A run against this source reports PnL,
notional and gas in USD. The Blockscout source reports in the chain's quote
asset. Do not compare numbers across the two without converting.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, Iterable, Iterator, List, Optional, Sequence

from ..http import JsonClient
from ..prices import PricePoint, PriceSeries
from ..trades import (BUY, DUST, ROTATION_IN, ROTATION_OUT, SELL, TRANSFER_IN,
                      TRANSFER_OUT, PositionTracker, Trade)

log = logging.getLogger(__name__)

GMGN_BASE = "https://openapi.gmgn.ai"
ROBINHOOD_CHAIN = "robinhood"
CHAINS = ("sol", "bsc", "base", "eth", "arbitrum", "hyperevm",
          "robinhood", "arc", "stable")

# Candle resolutions, coarsest-last. `30s` is the finest GMGN offers, which
# bounds how tightly a 5-minute post-sell horizon can be measured.
RESOLUTIONS = ("30s", "1m", "5m", "15m", "1h", "4h", "1d")

# GMGN activity `type` / `event_type` values mapped onto hoodtrack trade kinds.
EVENT_KINDS = {
    "buy": BUY,
    "sell": SELL,
    "transferin": TRANSFER_IN,
    "transfer_in": TRANSFER_IN,
    "transferout": TRANSFER_OUT,
    "transfer_out": TRANSFER_OUT,
    "transfer": TRANSFER_OUT,
    "add": ROTATION_IN,
    "remove": ROTATION_OUT,
}


def to_float(value, default: float = 0.0) -> float:
    """GMGN sends numerics as strings; empty and null are common."""
    if value is None or value == "":
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    # Reject NaN/inf rather than letting them poison downstream statistics.
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


class Gmgn:
    """Thin client over the two read endpoints hoodtrack needs."""

    def __init__(self, client: JsonClient, base_url: str = GMGN_BASE,
                 api_key: Optional[str] = None):
        self.base = base_url.rstrip("/")
        self.client = client
        self.api_key = api_key
        # X-APIKEY is a header, not a query param, so it stays out of URLs.
        if api_key and hasattr(client, "extra_headers"):
            client.extra_headers["X-APIKEY"] = api_key

    def _auth_params(self) -> Dict[str, str]:
        # Server validates timestamp within +/-5s and rejects a replayed
        # client_id within 7s, so both must be fresh on every single call.
        return {"timestamp": str(int(time.time())), "client_id": str(uuid.uuid4())}

    def _get(self, path: str, params: Dict) -> Dict:
        query = dict(params)
        query.update(self._auth_params())
        payload = self.client.get(f"{self.base}{path}", query)
        return self._unwrap(payload, path)

    @staticmethod
    def _unwrap(payload, path: str) -> Dict:
        """Strip the {code, data, message} envelope, surfacing API-level errors."""
        if not isinstance(payload, dict):
            return {}
        code = payload.get("code")
        # Success is 0 on this API; anything else carries an error message.
        if code not in (0, "0", None):
            message = payload.get("message") or payload.get("error") or ""
            raise RuntimeError(f"GMGN {path} returned code={code}: {message}")
        data = payload.get("data")
        return data if isinstance(data, dict) else {"list": data or []}

    def wallet_activity(self, chain: str, wallet: str, limit: int = 100,
                        max_pages: int = 50,
                        types: Sequence[str] = (),
                        stop_before: Optional[int] = None) -> Iterator[dict]:
        """Yield activity rows newest-first, following the `next` cursor."""
        cursor = None
        for page in range(max_pages):
            params: Dict = {"chain": chain, "wallet_address": wallet,
                            "limit": limit}
            if cursor:
                params["cursor"] = cursor
            if types:
                params["type"] = list(types)
            data = self._get("/v1/user/wallet_activity", params)
            rows = data.get("activities") or data.get("list") or []
            for row in rows:
                yield row
            cursor = data.get("next")
            if not rows or not cursor:
                return
            if stop_before is not None and rows:
                oldest = to_float(rows[-1].get("timestamp"))
                if oldest and oldest < stop_before:
                    return
        log.warning("hit max_pages=%d for %s activity; history truncated",
                    max_pages, wallet)

    def token_kline(self, chain: str, token: str, resolution: str = "1m",
                    start: Optional[int] = None,
                    end: Optional[int] = None) -> List[dict]:
        params: Dict = {"chain": chain, "address": token, "resolution": resolution}
        if start is not None:
            params["from"] = int(start)
        if end is not None:
            params["to"] = int(end)
        data = self._get("/v1/market/token_kline", params)
        rows = data.get("list") or []
        return rows if isinstance(rows, list) else []


# --- normalisation ------------------------------------------------------

def _token_of(row: dict) -> Dict:
    token = row.get("token")
    return token if isinstance(token, dict) else {}


def activity_kind(row: dict) -> Optional[str]:
    raw = str(row.get("event_type") or row.get("type") or "").strip().lower()
    return EVENT_KINDS.get(raw)


def parse_activity(row: dict, chain: str = ROBINHOOD_CHAIN) -> Optional[Trade]:
    """One GMGN activity row -> one hoodtrack Trade (USD-denominated)."""
    kind = activity_kind(row)
    if kind is None:
        return None

    token = _token_of(row)
    address = token.get("address") or token.get("token_address") or row.get("token_address")
    if not address:
        return None

    timestamp = int(to_float(row.get("timestamp")))
    if timestamp <= 0:
        return None

    token_amount = abs(to_float(row.get("token_amount")))
    # cost_usd is the documented size of the leg; quote_amount is the fallback.
    usd = abs(to_float(row.get("cost_usd")) or to_float(row.get("quote_amount"))
              or to_float(row.get("usd_value")))

    # Liquidity add/remove rows legitimately arrive with both amounts zero.
    # They carry no position change and must not become phantom trades.
    if token_amount <= DUST and usd <= DUST:
        return None

    price = to_float(row.get("price_usd"))
    if price <= 0 and token_amount > DUST and usd > DUST:
        price = usd / token_amount

    return Trade(
        tx_hash=str(row.get("tx_hash") or row.get("hash") or "").lower(),
        timestamp=timestamp,
        kind=kind,
        token=str(address).lower(),
        symbol=str(token.get("symbol") or "?").strip(),
        token_amount=token_amount,
        quote_amount=usd,
        quote_symbol="USD",
        price=price,
        wallets=[str(row.get("wallet_address") or "").lower()] if row.get("wallet_address") else [],
        gas_eth=to_float(row.get("gas_usd")),
    )


def trades_from_activity(rows: Iterable[dict],
                         chain: str = ROBINHOOD_CHAIN) -> List[Trade]:
    """Normalise, de-duplicate, order, and run FIFO position tracking.

    GMGN pages newest-first and the four wallets are queried separately, so the
    same fill can appear more than once; a trade is identified by
    (tx_hash, token, kind, amount) rather than tx_hash alone, because one
    transaction can legitimately carry several legs.
    """
    seen = set()
    trades: List[Trade] = []
    for row in rows:
        trade = parse_activity(row, chain)
        if trade is None:
            continue
        fingerprint = (trade.tx_hash, trade.token, trade.kind,
                       round(trade.token_amount, 12))
        if trade.tx_hash and fingerprint in seen:
            continue
        seen.add(fingerprint)
        trades.append(trade)

    trades.sort(key=lambda t: (t.timestamp, t.tx_hash, t.token))
    tracker = PositionTracker()
    return [tracker.apply(t) for t in trades]


def series_from_kline(token: str, rows: Iterable[dict]) -> PriceSeries:
    """GMGN candles -> PriceSeries.

    `price` is the candle close, which is what a fill can realistically get;
    `high` is carried separately so paper statistics can see the intrabar peak
    without letting the backtest execute against a wick.
    """
    points: List[PricePoint] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # `time` is documented as milliseconds, unlike activity's `timestamp`
        # which is seconds. Honour the contract per field rather than guessing
        # from magnitude -- a magnitude heuristic silently mis-scales any
        # timestamp near its threshold.
        if row.get("time") not in (None, ""):
            timestamp = int(to_float(row.get("time")) / 1000.0)
        else:
            timestamp = int(to_float(row.get("timestamp")))
        if timestamp <= 0:
            continue

        close = to_float(row.get("close"))
        high = to_float(row.get("high"))
        low = to_float(row.get("low"))
        # A candle missing close/high/low is unusable; missing volume is just 0.
        if close <= 0 or high <= 0 or low <= 0:
            continue

        volume_quote = to_float(row.get("volume"))   # USD turnover
        volume_base = to_float(row.get("amount"))    # token count
        if volume_base <= 0 and close > 0:
            volume_base = volume_quote / close

        points.append(PricePoint(
            timestamp=timestamp, price=close, volume_base=volume_base,
            volume_quote=volume_quote,
            tx_hash=str(row.get("source") or "kline"), pool="kline",
            high=max(high, close),
        ))
    # PriceSeries sorts on construction; GMGN does not guarantee ordering.
    return PriceSeries(token, points)
