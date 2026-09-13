"""Does the token keep pumping after he sells?

Every exit is scored on two different returns, and the gap between them is the
whole point:

  paper_return       max printed price in the window / his realised sell price
  realizable_return  best VWAP you could actually have sold his size into,
                     capped at `participation` of each print's volume

Reporting only the first is how backtests end up promising returns that no
position could have captured. Both are reported side by side throughout.
"""

from __future__ import annotations

import logging
import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .config import HORIZONS, PUMP_TIERS
from .prices import PriceSeries
from .trades import DUST, EXIT_KINDS, SELL, Trade

log = logging.getLogger(__name__)


@dataclass
class HorizonOutcome:
    label: str
    seconds: int
    close_return: Optional[float] = None       # price at t0+h vs sell price
    paper_return: Optional[float] = None       # best print in window
    realizable_return: Optional[float] = None  # best achievable VWAP for his size
    filled_fraction: Optional[float] = None
    seconds_to_peak: Optional[int] = None
    prints_in_window: int = 0
    quote_volume_in_window: float = 0.0


@dataclass
class ExitOutcome:
    tx_hash: str
    timestamp: int
    token: str
    symbol: str
    kind: str
    sell_price: float
    token_amount: float
    quote_amount: float
    is_full_exit: bool
    basis_is_incomplete: bool
    realized_pnl_quote: float
    hold_seconds: float
    wallets: List[str] = field(default_factory=list)
    horizons: Dict[str, HorizonOutcome] = field(default_factory=dict)

    def sold_the_top(self, label: str) -> Optional[bool]:
        h = self.horizons.get(label)
        if h is None or h.paper_return is None:
            return None
        return h.paper_return <= 0.0


def evaluate_exits(
    trades: Sequence[Trade],
    series_by_token: Dict[str, PriceSeries],
    horizons: Sequence[Tuple[str, int]] = tuple(HORIZONS),
    participation: float = 0.15,
    max_staleness: int = 3600,
) -> List[ExitOutcome]:
    """Score every exit against what the token did afterwards."""
    outcomes: List[ExitOutcome] = []
    for trade in trades:
        if trade.kind not in EXIT_KINDS or trade.token_amount <= DUST:
            continue
        series = series_by_token.get(trade.token)
        if series is None or not len(series):
            continue

        sell_price = trade.price
        if sell_price <= 0:
            # rotation_out has no quote leg: fall back to the market print.
            sell_price = series.price_at(trade.timestamp, max_staleness) or 0.0
        if sell_price <= 0:
            continue

        outcome = ExitOutcome(
            tx_hash=trade.tx_hash, timestamp=trade.timestamp, token=trade.token,
            symbol=trade.symbol, kind=trade.kind, sell_price=sell_price,
            token_amount=trade.token_amount, quote_amount=trade.quote_amount,
            is_full_exit=trade.is_full_exit,
            basis_is_incomplete=trade.basis_is_incomplete,
            realized_pnl_quote=trade.realized_pnl_quote,
            hold_seconds=trade.avg_hold_seconds, wallets=list(trade.wallets),
        )

        for label, seconds in horizons:
            t0, t1 = trade.timestamp, trade.timestamp + seconds
            ho = HorizonOutcome(label=label, seconds=seconds)
            pts = series.window(t0, t1)
            ho.prints_in_window = len(pts)
            ho.quote_volume_in_window = sum(p.volume_quote for p in pts)

            # A window with no prints at all is unobserved, not a zero return.
            if not pts:
                if series.end is not None and series.end >= t1:
                    ho.close_return = 0.0
                    ho.paper_return = 0.0
                    ho.realizable_return = 0.0
                    ho.seconds_to_peak = 0
                outcome.horizons[label] = ho
                continue

            best = series.max_in(t0, t1)
            if best:
                peak_price, peak_ts = best
                ho.paper_return = peak_price / sell_price - 1.0
                ho.seconds_to_peak = max(0, peak_ts - t0)

            close = series.close_at_horizon(t0, seconds, max_staleness=max_staleness)
            if close is not None:
                ho.close_return = close / sell_price - 1.0

            realizable = series.realizable_exit(t0, t1, trade.token_amount, participation)
            if realizable:
                vwap, fraction, _start = realizable
                ho.realizable_return = vwap / sell_price - 1.0
                ho.filled_fraction = fraction

            outcome.horizons[label] = ho
        outcomes.append(outcome)
    return outcomes


# --- aggregation --------------------------------------------------------

def _pct(numerator: int, denominator: int) -> Optional[float]:
    return (100.0 * numerator / denominator) if denominator else None


def bootstrap_ci(flags: Sequence[bool], iterations: int = 2000,
                 alpha: float = 0.05, seed: int = 7) -> Optional[Tuple[float, float]]:
    """Percentile bootstrap CI for a proportion. Small n is common here."""
    n = len(flags)
    if n < 5:
        return None
    rng = random.Random(seed)
    data = [1.0 if f else 0.0 for f in flags]
    means = []
    for _ in range(iterations):
        means.append(sum(rng.choice(data) for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * iterations)]
    hi = means[min(iterations - 1, int((1 - alpha / 2) * iterations))]
    return 100.0 * lo, 100.0 * hi


def _describe(values: Sequence[float]) -> Dict[str, Optional[float]]:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None,
                "p90": None, "stdev": None}
    vals_sorted = sorted(vals)

    def q(p: float) -> float:
        if len(vals_sorted) == 1:
            return vals_sorted[0]
        idx = p * (len(vals_sorted) - 1)
        lo, hi = int(idx), min(int(idx) + 1, len(vals_sorted) - 1)
        return vals_sorted[lo] + (vals_sorted[hi] - vals_sorted[lo]) * (idx - lo)

    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "p25": q(0.25),
        "p75": q(0.75),
        "p90": q(0.90),
        "stdev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def summarize(
    outcomes: Sequence[ExitOutcome],
    horizons: Sequence[Tuple[str, int]] = tuple(HORIZONS),
    tiers: Sequence[float] = tuple(PUMP_TIERS),
) -> Dict:
    """Headline table: for each horizon and tier, the share that kept pumping."""
    report: Dict = {"n_exits": len(outcomes), "horizons": {}}
    for label, seconds in horizons:
        paper = [o.horizons[label].paper_return for o in outcomes
                 if label in o.horizons and o.horizons[label].paper_return is not None]
        realiz = [o.horizons[label].realizable_return for o in outcomes
                  if label in o.horizons and o.horizons[label].realizable_return is not None]
        closes = [o.horizons[label].close_return for o in outcomes
                  if label in o.horizons and o.horizons[label].close_return is not None]
        peaks = [o.horizons[label].seconds_to_peak for o in outcomes
                 if label in o.horizons and o.horizons[label].seconds_to_peak is not None]

        tier_rows = {}
        for tier in tiers:
            paper_flags = [r >= tier for r in paper]
            realiz_flags = [r >= tier for r in realiz]
            tier_rows[f"{tier:.2f}"] = {
                "tier_pct": 100.0 * tier,
                "paper_pct": _pct(sum(paper_flags), len(paper_flags)),
                "paper_n": len(paper_flags),
                "paper_ci": bootstrap_ci(paper_flags),
                "realizable_pct": _pct(sum(realiz_flags), len(realiz_flags)),
                "realizable_n": len(realiz_flags),
                "realizable_ci": bootstrap_ci(realiz_flags),
            }

        report["horizons"][label] = {
            "seconds": seconds,
            "tiers": tier_rows,
            "paper_return": _describe(paper),
            "realizable_return": _describe(realiz),
            "close_return": _describe(closes),
            "seconds_to_peak": _describe(peaks),
            "sold_the_top_pct": _pct(sum(1 for r in paper if r <= 0), len(paper)),
        }
    return report


def segment(outcomes: Sequence[ExitOutcome], key) -> Dict[str, List[ExitOutcome]]:
    """Bucket outcomes by an arbitrary key function, for breakdown tables."""
    buckets: Dict[str, List[ExitOutcome]] = {}
    for outcome in outcomes:
        buckets.setdefault(str(key(outcome)), []).append(outcome)
    return buckets


def size_bucket(outcome: ExitOutcome) -> str:
    q = outcome.quote_amount
    if q <= 0:
        return "unpriced"
    for edge, name in ((0.1, "<0.1"), (0.5, "0.1-0.5"), (2.0, "0.5-2"), (10.0, "2-10")):
        if q < edge:
            return name
    return ">10"


def hold_bucket(outcome: ExitOutcome) -> str:
    h = outcome.hold_seconds
    if h <= 0:
        return "unknown"
    for edge, name in ((300, "<5m"), (3600, "5m-1h"), (14400, "1h-4h"),
                       (86400, "4h-24h")):
        if h < edge:
            return name
    return ">24h"
