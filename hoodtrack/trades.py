"""Reconstruct trades from raw transfers, router-agnostically.

Deliberately does NOT decode Uniswap Swap events. Decoding ties you to specific
router/pool ABIs and breaks on aggregators, v4 hooks and any new DEX. Instead we
compute the *entity's* net token delta per transaction: if a non-quote token went
up and a quote asset went down, that is a buy, whatever contract executed it.

The four wallets are treated as ONE entity, so a transfer between them nets to
zero and is correctly ignored rather than being double-counted as a sell+buy.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from .config import QUOTE_ADDRESSES, QUOTE_SYMBOLS
from .models import Transfer

log = logging.getLogger(__name__)

DUST = 1e-12

BUY = "buy"
SELL = "sell"
ROTATION_IN = "rotation_in"    # acquired by swapping another token for it
ROTATION_OUT = "rotation_out"  # disposed of by swapping it for another token
TRANSFER_IN = "transfer_in"    # airdrop, bridge-in, or funding from outside
TRANSFER_OUT = "transfer_out"  # sent to a CEX/bridge -- NOT a market sale
INTERNAL = "internal"

# Anything that removes the position from the entity's control on the open
# market. rotation_out counts: swapping A for B is still an exit from A.
EXIT_KINDS = (SELL, ROTATION_OUT)
ACQUIRE_KINDS = (BUY, TRANSFER_IN, ROTATION_IN)
DISPOSE_KINDS = (SELL, TRANSFER_OUT, ROTATION_OUT)


def is_quote(token: str, symbol: str, extra_quotes: Sequence[str] = ()) -> bool:
    if token in QUOTE_ADDRESSES or token in set(extra_quotes):
        return True
    return (symbol or "").upper() in QUOTE_SYMBOLS


@dataclass
class Trade:
    tx_hash: str
    timestamp: int
    kind: str
    token: str
    symbol: str
    token_amount: float          # always positive magnitude
    quote_amount: float          # always positive magnitude, 0 for transfers
    quote_symbol: str
    price: float                 # quote units per token unit, 0 if unpriced
    wallets: List[str] = field(default_factory=list)
    gas_eth: float = 0.0
    # Filled in by the position tracker:
    realized_pnl_quote: float = 0.0
    cost_basis_quote: float = 0.0
    position_before: float = 0.0
    position_after: float = 0.0
    is_full_exit: bool = False
    avg_hold_seconds: float = 0.0
    basis_is_incomplete: bool = False  # position partly acquired off-market

    @property
    def is_priced(self) -> bool:
        return self.price > 0 and self.token_amount > DUST


def group_by_tx(transfers: Iterable[Transfer]) -> Dict[str, List[Transfer]]:
    grouped: Dict[str, List[Transfer]] = defaultdict(list)
    for tr in transfers:
        grouped[tr.tx_hash].append(tr)
    return grouped


def net_deltas(transfers: Sequence[Transfer], entity: set) -> Dict[str, float]:
    """Net movement of each token for the entity as a whole, in token units."""
    deltas: Dict[str, float] = defaultdict(float)
    for tr in transfers:
        to_us = tr.receiver in entity
        from_us = tr.sender in entity
        if to_us == from_us:
            continue  # neither side is ours, or both are (an internal move)
        deltas[tr.token] += tr.amount if to_us else -tr.amount
    return {k: v for k, v in deltas.items() if abs(v) > DUST}


def classify_tx(
    transfers: Sequence[Transfer],
    entity: set,
    native_delta: float = 0.0,
    extra_quotes: Sequence[str] = (),
) -> List[Trade]:
    """Turn one transaction's transfers into zero or more Trade records."""
    if not transfers:
        return []
    deltas = net_deltas(transfers, entity)
    meta = {tr.token: tr for tr in transfers}

    quote_legs, base_legs = {}, {}
    for token, delta in deltas.items():
        tr = meta[token]
        (quote_legs if is_quote(token, tr.symbol, extra_quotes) else base_legs)[token] = delta
    if abs(native_delta) > DUST:
        quote_legs["native"] = quote_legs.get("native", 0.0) + native_delta

    if not base_legs:
        return []  # pure quote shuffle or fully internal

    timestamp = max(tr.timestamp for tr in transfers)
    tx_hash = transfers[0].tx_hash
    wallets = sorted({a for tr in transfers for a in (tr.sender, tr.receiver) if a in entity})

    quote_total = sum(quote_legs.values())
    quote_symbol = _dominant_quote_symbol(quote_legs, meta)

    gained = {t: d for t, d in base_legs.items() if d > 0}
    lost = {t: -d for t, d in base_legs.items() if d < 0}

    # Token-for-token rotation: no meaningful quote leg on either side.
    if gained and lost and abs(quote_total) <= DUST:
        out = []
        for token, amount in lost.items():
            out.append(_make(tx_hash, timestamp, ROTATION_OUT, token, meta, amount,
                             0.0, quote_symbol, wallets))
        for token, amount in gained.items():
            out.append(_make(tx_hash, timestamp, ROTATION_IN, token, meta, amount,
                             0.0, quote_symbol, wallets))
        return out

    trades = []
    for token, amount in gained.items():
        share = _share(amount, gained)
        spent = max(0.0, -quote_total) * share
        kind = BUY if spent > DUST else TRANSFER_IN
        trades.append(_make(tx_hash, timestamp, kind, token, meta, amount, spent, quote_symbol, wallets))
    for token, amount in lost.items():
        share = _share(amount, lost)
        received = max(0.0, quote_total) * share
        kind = SELL if received > DUST else TRANSFER_OUT
        trades.append(_make(tx_hash, timestamp, kind, token, meta, amount, received, quote_symbol, wallets))
    return trades


def _share(amount: float, bucket: Dict[str, float]) -> float:
    total = sum(bucket.values())
    return amount / total if total > DUST else 0.0


def _dominant_quote_symbol(quote_legs: Dict[str, float], meta: Dict[str, Transfer]) -> str:
    if not quote_legs:
        return "ETH"
    token = max(quote_legs, key=lambda t: abs(quote_legs[t]))
    if token == "native":
        return "ETH"
    tr = meta.get(token)
    return tr.symbol if tr else "ETH"


def _make(tx_hash, timestamp, kind, token, meta, token_amount, quote_amount,
          quote_symbol, wallets) -> Trade:
    tr = meta.get(token)
    price = quote_amount / token_amount if token_amount > DUST and quote_amount > 0 else 0.0
    return Trade(
        tx_hash=tx_hash, timestamp=timestamp, kind=kind, token=token,
        symbol=tr.symbol if tr else "?", token_amount=token_amount,
        quote_amount=quote_amount, quote_symbol=quote_symbol, price=price,
        wallets=list(wallets),
    )


@dataclass
class Lot:
    timestamp: int
    amount: float
    unit_cost: float
    synthetic: bool = False  # acquired off-market (airdrop/bridge), basis unknown


class PositionTracker:
    """FIFO inventory per token, producing realised PnL and exit metadata."""

    def __init__(self):
        self.lots: Dict[str, List[Lot]] = defaultdict(list)
        self.off_market: Dict[str, bool] = defaultdict(bool)

    def position(self, token: str) -> float:
        return sum(lot.amount for lot in self.lots[token])

    def apply(self, trade: Trade) -> Trade:
        token = trade.token
        trade.position_before = self.position(token)

        if trade.kind in ACQUIRE_KINDS and trade.token_amount > DUST:
            # Only a real buy establishes a known quote-denominated basis.
            synthetic = trade.kind != BUY
            if synthetic:
                self.off_market[token] = True
            unit_cost = trade.price if trade.price > 0 else 0.0
            self.lots[token].append(
                Lot(trade.timestamp, trade.token_amount, unit_cost, synthetic)
            )
            trade.cost_basis_quote = unit_cost * trade.token_amount

        elif trade.kind in DISPOSE_KINDS:
            consumed, basis, weighted_ts = self._consume(token, trade.token_amount)
            trade.cost_basis_quote = basis
            if trade.kind == SELL:
                trade.realized_pnl_quote = trade.quote_amount - basis
            if consumed > DUST:
                trade.avg_hold_seconds = max(0.0, trade.timestamp - weighted_ts)
            trade.basis_is_incomplete = self.off_market[token]

        trade.position_after = self.position(token)
        trade.is_full_exit = (
            trade.kind in EXIT_KINDS
            and trade.position_after <= max(DUST, trade.position_before * 1e-6)
        )
        return trade

    def _consume(self, token: str, amount: float):
        """FIFO-consume `amount` from inventory; return (consumed, basis, avg ts)."""
        remaining = amount
        basis = 0.0
        weighted_ts = 0.0
        consumed = 0.0
        lots = self.lots[token]
        while remaining > DUST and lots:
            lot = lots[0]
            take = min(lot.amount, remaining)
            basis += take * lot.unit_cost
            weighted_ts += take * lot.timestamp
            consumed += take
            lot.amount -= take
            remaining -= take
            if lot.amount <= DUST:
                lots.pop(0)
        if remaining > DUST:
            # Sold more than we ever saw bought: history is truncated or the
            # tokens arrived by a path we did not index. Basis for that slice
            # is unknown, not zero -- flag rather than fabricate a profit.
            self.off_market[token] = True
        return consumed, basis, (weighted_ts / consumed if consumed > DUST else 0.0)


def build_trades(
    transfers: Iterable[Transfer],
    entity: Iterable[str],
    native_by_tx: Optional[Dict[str, float]] = None,
    gas_by_tx: Optional[Dict[str, float]] = None,
    extra_quotes: Sequence[str] = (),
) -> List[Trade]:
    """Full pipeline: raw transfers -> chronologically tracked trades."""
    entity_set = {a.lower() for a in entity}
    native_by_tx = native_by_tx or {}
    gas_by_tx = gas_by_tx or {}

    grouped = group_by_tx(transfers)
    raw: List[Trade] = []
    for tx_hash, legs in grouped.items():
        for trade in classify_tx(legs, entity_set, native_by_tx.get(tx_hash, 0.0), extra_quotes):
            trade.gas_eth = gas_by_tx.get(tx_hash, 0.0)
            raw.append(trade)

    raw.sort(key=lambda t: (t.timestamp, t.tx_hash, t.token))
    tracker = PositionTracker()
    return [tracker.apply(t) for t in raw]
