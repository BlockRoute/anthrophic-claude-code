"""Per-token price history rebuilt from on-chain pool flow.

No price API is used. For any AMM, a swap moves the base token and the quote
token through the pool in opposite directions inside one transaction, so

    price = |quote delta of the pool| / |base delta of the pool|

That expression is identical for Uniswap v2, v3 and v4 and for every aggregator
and router on top of them, which is why it is preferred to event decoding.

It also yields per-print *volume*, which is what makes the realisability model
below possible: a +400% wick on $80 of volume is not an exit you could have hit.
"""

from __future__ import annotations

import bisect
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import Transfer, parse_transfer
from .trades import DUST, is_quote

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PricePoint:
    timestamp: int
    price: float          # quote units per base token
    volume_base: float    # base tokens that changed hands in this print
    volume_quote: float
    tx_hash: str
    pool: str


class PriceSeries:
    """Chronologically sorted price prints for one token, with window queries."""

    def __init__(self, token: str, points: Sequence[PricePoint]):
        self.token = token
        self.points: List[PricePoint] = sorted(points, key=lambda p: p.timestamp)
        self._times = [p.timestamp for p in self.points]

    def __len__(self) -> int:
        return len(self.points)

    @property
    def start(self) -> Optional[int]:
        return self._times[0] if self._times else None

    @property
    def end(self) -> Optional[int]:
        return self._times[-1] if self._times else None

    def window(self, t0: int, t1: int) -> List[PricePoint]:
        """Prints in the half-open interval (t0, t1]."""
        lo = bisect.bisect_right(self._times, t0)
        hi = bisect.bisect_right(self._times, t1)
        return self.points[lo:hi]

    def price_at(self, t: int, max_staleness: int = 3600) -> Optional[float]:
        """Most recent print at or before t, if it is not too stale."""
        idx = bisect.bisect_right(self._times, t) - 1
        if idx < 0:
            return None
        point = self.points[idx]
        if t - point.timestamp > max_staleness:
            return None
        return point.price

    def max_in(self, t0: int, t1: int) -> Optional[Tuple[float, int]]:
        """Highest print in the window and when it happened."""
        pts = self.window(t0, t1)
        if not pts:
            return None
        best = max(pts, key=lambda p: p.price)
        return best.price, best.timestamp

    def close_at_horizon(self, t0: int, horizon: int,
                         max_staleness: int = 3600) -> Optional[float]:
        return self.price_at(t0 + horizon, max_staleness=max_staleness)

    def fill_from(self, t_start: int, size_base: float,
                  participation: float = 0.15,
                  max_seconds: int = 86400) -> Optional[Tuple[float, float, int]]:
        """VWAP of filling `size_base` starting at a specific moment.

        Unlike `realizable_exit`, which searches for the best moment to start,
        this models an order you actually placed at `t_start` and worked forward
        at `participation` of volume. Used for every simulated fill so the
        backtest cannot buy or sell more than the market could absorb.

        Returns (vwap, filled_fraction, completion_timestamp).
        """
        if size_base <= DUST:
            return None
        pts = self.window(t_start - 1, t_start + max_seconds)
        if not pts:
            return None
        remaining = size_base
        proceeds = 0.0
        end_ts = pts[0].timestamp
        for point in pts:
            if remaining <= DUST:
                break
            capacity = point.volume_base * participation
            if capacity <= 0:
                continue
            fill = min(remaining, capacity)
            proceeds += fill * point.price
            remaining -= fill
            end_ts = point.timestamp
        filled = size_base - remaining
        if filled <= DUST:
            return None
        return proceeds / filled, filled / size_base, end_ts

    def realizable_exit(self, t0: int, t1: int, size_base: float,
                        participation: float = 0.15,
                        max_starts: int = 120) -> Optional[Tuple[float, float, int]]:
        """Best VWAP actually achievable selling `size_base` inside (t0, t1].

        Assumes you can be at most `participation` of each print's volume, and
        that you must sell forward in time from whatever moment you start. This
        is the honest version of "the token kept pumping": it charges you for
        the liquidity you would have had to eat.

        Returns (vwap, filled_fraction, start_timestamp).
        """
        pts = self.window(t0, t1)
        if not pts or size_base <= DUST:
            return None

        # Only prints above the median are plausible places to start selling;
        # cap the candidate set so this stays linear-ish in practice.
        ranked = sorted(range(len(pts)), key=lambda i: pts[i].price, reverse=True)
        candidates = ranked[:max_starts]

        best = None
        for start in candidates:
            remaining = size_base
            proceeds = 0.0
            for point in pts[start:]:
                if remaining <= DUST:
                    break
                capacity = point.volume_base * participation
                if capacity <= 0:
                    continue
                fill = min(remaining, capacity)
                proceeds += fill * point.price
                remaining -= fill
            filled = size_base - remaining
            if filled <= DUST:
                continue
            vwap = proceeds / filled
            fraction = filled / size_base
            # Prefer the higher VWAP; break ties toward the more complete fill.
            key = (vwap, fraction)
            if best is None or key > best[0]:
                best = (key, vwap, fraction, pts[start].timestamp)
        if best is None:
            return None
        return best[1], best[2], best[3]


def infer_pools(transfers: Iterable[Transfer], token: str,
                top_n: int = 4, min_hits: int = 5) -> List[str]:
    """Guess which counterparties are AMM pools, by how often they appear.

    A pool is on one side of nearly every swap of a token, so frequency is a
    strong signal. Callers should confirm with `looks_like_pool`.
    """
    counts: Counter = Counter()
    for tr in transfers:
        if tr.token != token:
            continue
        for side in (tr.sender, tr.receiver):
            if side and int(side, 16) != 0:
                counts[side] += 1
    return [addr for addr, hits in counts.most_common(top_n * 4)
            if hits >= min_hits][:top_n]


def looks_like_pool(pool_transfers: Sequence[Transfer], token: str,
                    extra_quotes: Sequence[str] = ()) -> bool:
    """True if this address moves both the base token and a quote asset."""
    saw_base = saw_quote = False
    for tr in pool_transfers:
        if tr.token == token:
            saw_base = True
        elif is_quote(tr.token, tr.symbol, extra_quotes):
            saw_quote = True
        if saw_base and saw_quote:
            return True
    return False


def series_from_pool_transfers(pool: str, token: str,
                               transfers: Iterable[Transfer],
                               extra_quotes: Sequence[str] = ()) -> List[PricePoint]:
    """Pair the base and quote legs of each swap through one pool."""
    by_tx: Dict[str, List[Transfer]] = defaultdict(list)
    for tr in transfers:
        by_tx[tr.tx_hash].append(tr)

    points: List[PricePoint] = []
    for tx_hash, legs in by_tx.items():
        base_delta = 0.0
        quote_delta = 0.0
        timestamp = 0
        for tr in legs:
            if tr.sender == pool:
                signed = -tr.amount
            elif tr.receiver == pool:
                signed = tr.amount
            else:
                continue
            timestamp = max(timestamp, tr.timestamp)
            if tr.token == token:
                base_delta += signed
            elif is_quote(tr.token, tr.symbol, extra_quotes):
                quote_delta += signed

        # A genuine swap moves both sides in opposite directions.
        if abs(base_delta) <= DUST or abs(quote_delta) <= DUST:
            continue
        if (base_delta > 0) == (quote_delta > 0):
            continue  # both in or both out: liquidity add/remove, not a trade

        price = abs(quote_delta) / abs(base_delta)
        if price <= 0 or price != price:  # guard against NaN
            continue
        points.append(PricePoint(
            timestamp=timestamp, price=price, volume_base=abs(base_delta),
            volume_quote=abs(quote_delta), tx_hash=tx_hash, pool=pool,
        ))
    return points


def build_series(token: str, pool_transfer_sets: Dict[str, Iterable[Transfer]],
                 extra_quotes: Sequence[str] = ()) -> PriceSeries:
    """Merge prints from every pool that trades `token`."""
    points: List[PricePoint] = []
    for pool, transfers in pool_transfer_sets.items():
        points.extend(series_from_pool_transfers(pool, token, transfers, extra_quotes))
    return PriceSeries(token, points)


def series_from_raw(token: str, raw_by_pool: Dict[str, List[dict]],
                    extra_quotes: Sequence[str] = ()) -> PriceSeries:
    parsed = {}
    for pool, items in raw_by_pool.items():
        parsed[pool] = [t for t in (parse_transfer(i) for i in items) if t]
    return build_series(token, parsed, extra_quotes)
