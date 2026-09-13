"""Pull raw chain data once, cache it on disk, and reuse it forever.

Blockscout pages newest-first, so every collector takes a `stop_before` epoch
and abandons pagination as soon as it has walked past the period of interest.
Without that bound, fetching the price history of a busy memecoin would page
through its entire life.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from .config import IngestParams
from .models import Transfer, gas_cost_eth, parse_native_from_tx, parse_transfer
from .prices import PriceSeries, build_series, infer_pools, looks_like_pool
from .sources import Blockscout
from .trades import is_quote

log = logging.getLogger(__name__)


class Cache:
    """Plain JSON on disk. Re-running analysis must never re-hit the network."""

    def __init__(self, root: str = "data/cache"):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def path(self, key: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return os.path.join(self.root, f"{safe}.json")

    def get(self, key: str, max_age_seconds: Optional[int] = None):
        path = self.path(key)
        if not os.path.exists(path):
            return None
        if max_age_seconds is not None:
            if time.time() - os.path.getmtime(path) > max_age_seconds:
                return None
        try:
            with open(path) as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            log.warning("corrupt cache entry %s; refetching", path)
            return None

    def put(self, key: str, value) -> None:
        tmp = self.path(key) + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(value, fh)
        os.replace(tmp, self.path(key))  # atomic; a killed run leaves no half file


def collect(items: Iterable[dict], stop_before: Optional[int] = None,
            limit: Optional[int] = None) -> List[dict]:
    """Drain a Blockscout page iterator, stopping once we are past `stop_before`."""
    out: List[dict] = []
    for item in items:
        out.append(item)
        if limit and len(out) >= limit:
            break
        if stop_before is not None and len(out) % 50 == 0:
            ts = _ts_of(item)
            if ts is not None and ts < stop_before:
                break
    return out


def _ts_of(item: dict) -> Optional[int]:
    from .models import parse_timestamp
    return parse_timestamp(item.get("timestamp") or item.get("block_timestamp"))


def fetch_entity_activity(explorer: Blockscout, wallets: Sequence[str],
                          cache: Cache, params: IngestParams,
                          refresh: bool = False) -> Dict[str, List[dict]]:
    """Raw token transfers and transactions for every wallet in the entity."""
    raw: Dict[str, List[dict]] = {"transfers": [], "transactions": []}
    for wallet in wallets:
        wallet = wallet.lower()

        key = f"transfers_{wallet}"
        items = None if refresh else cache.get(key)
        if items is None:
            log.info("fetching token transfers for %s", wallet)
            items = collect(explorer.address_token_transfers(
                wallet, max_pages=params.max_pages_per_address))
            cache.put(key, items)
        log.info("  %s: %d token transfers", wallet, len(items))
        raw["transfers"].extend(items)

        key = f"txs_{wallet}"
        txs = None if refresh else cache.get(key)
        if txs is None:
            log.info("fetching transactions for %s", wallet)
            txs = collect(explorer.address_transactions(
                wallet, max_pages=params.max_pages_per_address))
            cache.put(key, txs)
        log.info("  %s: %d transactions", wallet, len(txs))
        raw["transactions"].extend(txs)
    return raw


def parse_activity(raw: Dict[str, List[dict]], wallets: Sequence[str]):
    """Raw payloads -> (transfers, native delta by tx, gas by tx)."""
    entity = {w.lower() for w in wallets}
    seen = set()
    transfers: List[Transfer] = []
    for item in raw.get("transfers", []):
        tr = parse_transfer(item)
        if not tr:
            continue
        # The same transfer appears under both wallets when it is internal.
        fingerprint = (tr.tx_hash, tr.log_index, tr.token, tr.sender, tr.receiver)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        transfers.append(tr)

    native_by_tx: Dict[str, float] = {}
    gas_by_tx: Dict[str, float] = {}
    seen_tx = set()
    for item in raw.get("transactions", []):
        flow = parse_native_from_tx(item)
        if not flow or flow.tx_hash in seen_tx:
            continue
        seen_tx.add(flow.tx_hash)
        delta = 0.0
        if flow.sender in entity:
            delta -= flow.amount
        if flow.receiver in entity:
            delta += flow.amount
        if abs(delta) > 0:
            native_by_tx[flow.tx_hash] = delta
        if flow.sender in entity:
            gas_by_tx[flow.tx_hash] = gas_cost_eth(item)
    return transfers, native_by_tx, gas_by_tx


def traded_tokens(transfers: Sequence[Transfer],
                  extra_quotes: Sequence[str] = ()) -> List[str]:
    tokens = {tr.token for tr in transfers
              if not is_quote(tr.token, tr.symbol, extra_quotes)}
    return sorted(tokens)


def fetch_price_series(explorer: Blockscout, tokens: Sequence[str],
                       cache: Cache, params: IngestParams,
                       window_by_token: Optional[Dict[str, int]] = None,
                       refresh: bool = False,
                       progress: Optional[Callable[[int, int, str], None]] = None
                       ) -> Dict[str, PriceSeries]:
    """Build a price series per token from the flow through its pools."""
    window_by_token = window_by_token or {}
    out: Dict[str, PriceSeries] = {}

    for idx, token in enumerate(tokens, 1):
        if progress:
            progress(idx, len(tokens), token)
        stop_before = window_by_token.get(token)

        key = f"token_transfers_{token}"
        token_items = None if refresh else cache.get(key)
        if token_items is None:
            token_items = collect(
                explorer.token_transfers(token, max_pages=params.max_pages_per_token),
                stop_before=stop_before)
            cache.put(key, token_items)

        parsed = [t for t in (parse_transfer(i) for i in token_items) if t]
        if not parsed:
            out[token] = PriceSeries(token, [])
            continue

        pools = infer_pools(parsed, token)
        pool_sets: Dict[str, List[Transfer]] = {}
        for pool in pools:
            pkey = f"pool_transfers_{pool}"
            pool_items = None if refresh else cache.get(pkey)
            if pool_items is None:
                pool_items = collect(
                    explorer.address_token_transfers(
                        pool, max_pages=params.max_pages_per_token),
                    stop_before=stop_before)
                cache.put(pkey, pool_items)
            pool_parsed = [t for t in (parse_transfer(i) for i in pool_items) if t]
            if looks_like_pool(pool_parsed, token):
                pool_sets[pool] = pool_parsed

        out[token] = build_series(token, pool_sets)
        log.info("  %s: %d price prints across %d pools",
                 token[:10], len(out[token]), len(pool_sets))
    return out


def price_windows(trades, lookahead: int) -> Dict[str, int]:
    """Earliest timestamp we need price data from, per token."""
    earliest: Dict[str, int] = {}
    for t in trades:
        cur = earliest.get(t.token)
        if cur is None or t.timestamp < cur:
            earliest[t.token] = t.timestamp
    return {k: v - 3600 for k, v in earliest.items()}
