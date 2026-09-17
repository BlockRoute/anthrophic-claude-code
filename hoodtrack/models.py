"""Normalised records plus tolerant parsers for Blockscout payloads.

Blockscout field names drift between releases and between self-hosted and Pro
deployments (`address` vs `address_hash`, `transaction_hash` vs `tx_hash`,
decimals as int vs str). Every parser here accepts the known spellings so the
pipeline does not silently drop rows when the explorer is upgraded.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _first(d: dict, *keys, default=None):
    for key in keys:
        if isinstance(d, dict) and d.get(key) is not None:
            return d[key]
    return default


def norm_addr(value: Any) -> Optional[str]:
    """Accept a bare string or a Blockscout address object; return lowercase hex."""
    if value is None:
        return None
    if isinstance(value, dict):
        value = _first(value, "hash", "address", "address_hash")
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    return value.lower()


def parse_timestamp(value: Any) -> Optional[int]:
    """ISO-8601 string or unix seconds -> unix seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        text = value.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return int(parsed.timestamp())
    return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, str):
            value = value.strip()
            return int(value, 16) if value.startswith("0x") else int(value)
        return int(value)
    except (TypeError, ValueError):
        return default


def scale(raw: Any, decimals: Any) -> float:
    """Convert a raw integer amount to human units without float precision loss."""
    try:
        raw_int = Decimal(_to_int(raw))
        dec = _to_int(decimals, 18)
        dec = max(0, min(dec, 60))
        return float(raw_int / (Decimal(10) ** dec))
    except (InvalidOperation, ValueError):
        return 0.0


@dataclass(frozen=True)
class Transfer:
    tx_hash: str
    block: int
    timestamp: int
    token: str
    symbol: str
    decimals: int
    sender: str
    receiver: str
    amount: float
    log_index: int

    @property
    def is_mint(self) -> bool:
        return self.sender == ZERO_ADDRESS

    @property
    def is_burn(self) -> bool:
        return self.receiver == ZERO_ADDRESS


def parse_transfer(item: dict) -> Optional[Transfer]:
    """Normalise one Blockscout token-transfer item; None if unusable."""
    if not isinstance(item, dict):
        return None
    token = item.get("token") or {}
    token_addr = norm_addr(_first(token, "address", "address_hash"))
    sender = norm_addr(_first(item, "from", "from_address"))
    receiver = norm_addr(_first(item, "to", "to_address"))
    tx_hash = _first(item, "transaction_hash", "tx_hash", "hash")
    if not token_addr or not sender or not receiver or not tx_hash:
        return None

    # ERC-721/1155 carry no fungible amount; they are not trades for our purposes.
    token_type = (token.get("type") or "").upper()
    if token_type and "20" not in token_type:
        return None

    total = _first(item, "total", "value", default={})
    if isinstance(total, dict):
        raw = _first(total, "value", "amount", default="0")
        decimals = _first(total, "decimals", default=token.get("decimals", 18))
    else:
        raw = total
        decimals = token.get("decimals", 18)

    return Transfer(
        tx_hash=str(tx_hash).lower(),
        block=_to_int(_first(item, "block_number", "block", "blockNumber")),
        timestamp=parse_timestamp(_first(item, "timestamp", "block_timestamp")) or 0,
        token=token_addr,
        symbol=(token.get("symbol") or "?").strip(),
        decimals=_to_int(decimals, 18),
        sender=sender,
        receiver=receiver,
        amount=scale(raw, decimals),
        log_index=_to_int(_first(item, "log_index", "logIndex", "index"), 0),
    )


@dataclass(frozen=True)
class NativeFlow:
    """Native ETH movement attributable to a transaction."""

    tx_hash: str
    timestamp: int
    sender: str
    receiver: str
    amount: float


def parse_native_from_tx(item: dict) -> Optional[NativeFlow]:
    tx_hash = _first(item, "hash", "transaction_hash", "tx_hash")
    sender = norm_addr(_first(item, "from", "from_address"))
    receiver = norm_addr(_first(item, "to", "to_address"))
    if not tx_hash or not sender:
        return None
    return NativeFlow(
        tx_hash=str(tx_hash).lower(),
        timestamp=parse_timestamp(_first(item, "timestamp", "block_timestamp")) or 0,
        sender=sender,
        receiver=receiver or ZERO_ADDRESS,
        amount=scale(_first(item, "value", default="0"), 18),
    )


def gas_cost_eth(item: dict) -> float:
    """Actual gas paid by a transaction, in ETH."""
    used = _to_int(_first(item, "gas_used", "gasUsed"), 0)
    price = _to_int(_first(item, "gas_price", "gasPrice"), 0)
    if not used or not price:
        fee = _first(item, "fee", default=None)
        if isinstance(fee, dict):
            return scale(fee.get("value", 0), 18)
        return 0.0
    return scale(used * price, 18)
