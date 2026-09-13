"""Copy-trading simulation across three exit models.

Entry is identical in all three: when the entity opens a position in a token,
you open one `latency_seconds` later, at whatever the market actually offered
then, filling at no more than `participation` of traded volume. What differs is
how you get out:

  mirror     sell the same fraction of your position he sells, when he sells it
  hold       ignore his exits; run your own take-profit / stop / trailing stop
  scale_out  sell part at his exit, let the rest ride on the `hold` rules

Only the entity's *first* buy of a token opens a position. His later adds are
deliberately ignored so every model trades identical size on identical signals
and the comparison isolates the exit rule.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .config import BacktestParams
from .prices import PriceSeries
from .trades import BUY, DUST, EXIT_KINDS, Trade

log = logging.getLogger(__name__)

MODEL_MIRROR = "mirror"
MODEL_HOLD = "hold"
MODEL_SCALE_OUT = "scale_out"
MODELS = (MODEL_MIRROR, MODEL_HOLD, MODEL_SCALE_OUT)

MIN_FILL_FRACTION = 0.05  # below this the entry is treated as unfillable


@dataclass
class ExitLeg:
    timestamp: int
    reason: str
    tokens: float
    price: float
    proceeds_eth: float


@dataclass
class PositionResult:
    model: str
    token: str
    symbol: str
    signal_ts: int
    entry_ts: int
    entry_price: float
    tokens: float
    cost_eth: float
    proceeds_eth: float = 0.0
    legs: List[ExitLeg] = field(default_factory=list)
    unsold_tokens: float = 0.0
    skipped_reason: Optional[str] = None

    @property
    def exit_ts(self) -> int:
        return self.legs[-1].timestamp if self.legs else self.entry_ts

    @property
    def pnl_eth(self) -> float:
        return self.proceeds_eth - self.cost_eth

    @property
    def roi(self) -> float:
        return self.pnl_eth / self.cost_eth if self.cost_eth > DUST else 0.0

    @property
    def hold_seconds(self) -> int:
        return max(0, self.exit_ts - self.entry_ts)


def _buy_cost_multiplier(p: BacktestParams) -> float:
    return 1.0 + (p.costs.swap_fee_bps + p.costs.slippage_bps) / 10000.0


def _sell_proceeds_multiplier(p: BacktestParams) -> float:
    return 1.0 - (p.costs.swap_fee_bps + p.costs.slippage_bps) / 10000.0


def entity_episodes(trades: Sequence[Trade]) -> List[Tuple[Trade, List[Trade]]]:
    """Pair each opening buy with the exits that follow it, per token."""
    by_token: Dict[str, List[Trade]] = {}
    for t in trades:
        by_token.setdefault(t.token, []).append(t)

    episodes = []
    for token, seq in by_token.items():
        seq = sorted(seq, key=lambda t: (t.timestamp, t.tx_hash))
        open_buy: Optional[Trade] = None
        exits: List[Trade] = []
        for t in seq:
            if t.kind == BUY and open_buy is None and t.position_before <= DUST:
                open_buy, exits = t, []
            elif open_buy is not None and t.kind in EXIT_KINDS:
                exits.append(t)
                if t.is_full_exit:
                    episodes.append((open_buy, exits))
                    open_buy, exits = None, []
        if open_buy is not None:
            episodes.append((open_buy, exits))
    episodes.sort(key=lambda e: e[0].timestamp)
    return episodes


def _open_position(model: str, buy: Trade, series: PriceSeries,
                   params: BacktestParams) -> PositionResult:
    latency = int(params.costs.latency_seconds)
    entry_ts = buy.timestamp + latency
    reference = series.price_at(entry_ts, max_staleness=3600) or buy.price
    if reference <= 0:
        return PositionResult(model, buy.token, buy.symbol, buy.timestamp, entry_ts,
                              0.0, 0.0, 0.0, skipped_reason="no reference price")

    target_tokens = params.notional_eth / reference
    fill = series.fill_from(entry_ts, target_tokens, params.participation_rate,
                            max_seconds=600)
    if not fill:
        return PositionResult(model, buy.token, buy.symbol, buy.timestamp, entry_ts,
                              0.0, 0.0, 0.0, skipped_reason="no liquidity at entry")
    vwap, fraction, done_ts = fill
    if fraction < MIN_FILL_FRACTION:
        return PositionResult(model, buy.token, buy.symbol, buy.timestamp, entry_ts,
                              0.0, 0.0, 0.0, skipped_reason="entry unfillable")

    entry_price = vwap * _buy_cost_multiplier(params)
    tokens = target_tokens * fraction
    cost = tokens * entry_price + params.costs.gas_eth_per_swap
    return PositionResult(model, buy.token, buy.symbol, buy.timestamp, done_ts,
                          entry_price, tokens, cost)


def _sell(pos: PositionResult, series: PriceSeries, ts: int, tokens: float,
          reason: str, params: BacktestParams) -> float:
    """Execute a partial or full exit; returns tokens actually sold."""
    if tokens <= DUST:
        return 0.0
    fill = series.fill_from(ts, tokens, params.participation_rate, max_seconds=86400)
    if not fill:
        return 0.0
    vwap, fraction, done_ts = fill
    sold = tokens * fraction
    proceeds = sold * vwap * _sell_proceeds_multiplier(params) - params.costs.gas_eth_per_swap
    pos.proceeds_eth += max(0.0, proceeds)
    pos.legs.append(ExitLeg(done_ts, reason, sold, vwap, max(0.0, proceeds)))
    return sold


def _rule_based_exit(pos: PositionResult, series: PriceSeries, remaining: float,
                     from_ts: int, params: BacktestParams,
                     peak: Optional[float] = None) -> float:
    """Walk prints forward applying TP / SL / trailing / time stop."""
    if remaining <= DUST:
        return 0.0
    deadline = pos.entry_ts + params.max_hold_seconds
    tp = pos.entry_price * params.take_profit_mult
    sl = pos.entry_price * (1.0 - params.stop_loss_pct)
    peak = peak if peak is not None else pos.entry_price

    for point in series.window(from_ts - 1, deadline):
        peak = max(peak, point.price)
        reason = None
        if point.price >= tp:
            reason = "take_profit"
        elif point.price <= sl:
            reason = "stop_loss"
        elif peak > pos.entry_price and point.price <= peak * (1.0 - params.trailing_stop_pct):
            reason = "trailing_stop"
        if reason:
            latency = int(params.costs.latency_seconds)
            return _sell(pos, series, point.timestamp + latency, remaining, reason, params)

    return _sell(pos, series, deadline, remaining, "time_stop", params)


def simulate(model: str, buy: Trade, exits: Sequence[Trade], series: PriceSeries,
             params: BacktestParams) -> PositionResult:
    pos = _open_position(model, buy, series, params)
    if pos.skipped_reason:
        return pos
    remaining = pos.tokens
    latency = int(params.costs.latency_seconds)

    if model == MODEL_MIRROR:
        for ex in exits:
            if remaining <= DUST:
                break
            share = _his_exit_share(ex)
            sold = _sell(pos, series, ex.timestamp + latency, remaining * share,
                         "mirror", params)
            remaining -= sold
        if remaining > DUST:
            # He never fully exited within our data: close at the time stop.
            remaining -= _sell(pos, series, pos.entry_ts + params.max_hold_seconds,
                               remaining, "time_stop", params)

    elif model == MODEL_HOLD:
        remaining -= _rule_based_exit(pos, series, remaining, pos.entry_ts, params)

    elif model == MODEL_SCALE_OUT:
        if exits:
            first = exits[0]
            sold = _sell(pos, series, first.timestamp + latency,
                         remaining * params.scale_out_fraction, "scale_out", params)
            remaining -= sold
            remaining -= _rule_based_exit(pos, series, remaining,
                                          first.timestamp + latency, params)
        else:
            remaining -= _rule_based_exit(pos, series, remaining, pos.entry_ts, params)
    else:
        raise ValueError(f"unknown model: {model}")

    pos.unsold_tokens = max(0.0, remaining)
    return pos


def _his_exit_share(trade: Trade) -> float:
    """Fraction of his own position that this exit represents."""
    if trade.position_before <= DUST:
        return 1.0
    return min(1.0, max(0.0, trade.token_amount / trade.position_before))


def apply_concurrency_cap(results: Sequence[PositionResult],
                          max_concurrent: int) -> List[PositionResult]:
    """Greedy chronological admission: you only have so much capital at once."""
    accepted: List[PositionResult] = []
    open_until: List[int] = []
    for pos in sorted(results, key=lambda p: p.entry_ts):
        if pos.skipped_reason:
            continue
        open_until = [t for t in open_until if t > pos.entry_ts]
        if len(open_until) >= max_concurrent:
            pos.skipped_reason = "concurrency cap"
            continue
        open_until.append(pos.exit_ts)
        accepted.append(pos)
    return accepted


def run_backtest(trades: Sequence[Trade], series_by_token: Dict[str, PriceSeries],
                 params: BacktestParams,
                 models: Sequence[str] = MODELS) -> Dict[str, Dict]:
    episodes = entity_episodes(trades)
    out: Dict[str, Dict] = {}
    for model in models:
        raw: List[PositionResult] = []
        for buy, exits in episodes:
            series = series_by_token.get(buy.token)
            if series is None or not len(series):
                continue
            raw.append(simulate(model, buy, exits, series, params))
        accepted = apply_concurrency_cap(raw, params.max_concurrent)
        out[model] = {
            "positions": accepted,
            "skipped": [p for p in raw if p.skipped_reason],
            "metrics": metrics(accepted),
        }
    return out


def metrics(positions: Sequence[PositionResult]) -> Dict:
    if not positions:
        return {"n": 0}
    pnls = [p.pnl_eth for p in positions]
    wins = [p for p in positions if p.pnl_eth > 0]
    losses = [p for p in positions if p.pnl_eth <= 0]
    deployed = sum(p.cost_eth for p in positions)
    total = sum(pnls)

    ordered = sorted(positions, key=lambda p: p.exit_ts)
    equity, peak, max_dd = 0.0, 0.0, 0.0
    curve = []
    for pos in ordered:
        equity += pos.pnl_eth
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
        curve.append((pos.exit_ts, equity))

    gross_win = sum(p.pnl_eth for p in wins)
    gross_loss = -sum(p.pnl_eth for p in losses)
    rois = sorted(p.roi for p in positions)
    mid = len(rois) // 2
    median_roi = rois[mid] if len(rois) % 2 else (rois[mid - 1] + rois[mid]) / 2

    return {
        "n": len(positions),
        "net_pnl_eth": total,
        "deployed_eth": deployed,
        "return_on_deployed_pct": 100.0 * total / deployed if deployed > DUST else None,
        "win_rate_pct": 100.0 * len(wins) / len(positions),
        "avg_win_eth": (gross_win / len(wins)) if wins else 0.0,
        "avg_loss_eth": (-gross_loss / len(losses)) if losses else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss > DUST else None,
        "median_roi_pct": 100.0 * median_roi,
        "max_drawdown_eth": max_dd,
        "median_hold_seconds": sorted(p.hold_seconds for p in positions)[len(positions) // 2],
        "equity_curve": curve,
    }
