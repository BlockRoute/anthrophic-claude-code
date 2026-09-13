"""Console and JSON rendering of the analysis."""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence

from .backtest import MODELS
from .pump import ExitOutcome, hold_bucket, segment, size_bucket, summarize
from .trades import BUY, DUST, EXIT_KINDS, SELL, TRANSFER_IN, TRANSFER_OUT, Trade


def _fmt(value: Optional[float], suffix: str = "", places: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{places}f}{suffix}"


def _pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:5.1f}%"


def _ret(value: Optional[float]) -> str:
    """Fractional return -> signed percentage."""
    return "n/a" if value is None else f"{100.0 * value:+.1f}%"


def _dur(seconds: Optional[float]) -> str:
    if seconds is None:
        return "n/a"
    seconds = int(seconds)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds / size:.1f}{unit}"
    return f"{seconds}s"


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "  ".join("-" * w for w in widths)
    body = ["  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row))
            for row in rows]
    return "\n".join([line, sep] + body)


def render_profile(trades: Sequence[Trade], wallets: Sequence[str],
                   unit: str = "ETH") -> str:
    buys = [t for t in trades if t.kind == BUY]
    sells = [t for t in trades if t.kind == SELL]
    exits = [t for t in trades if t.kind in EXIT_KINDS]
    tokens = {t.token for t in trades}
    realized = sum(t.realized_pnl_quote for t in sells)
    spent = sum(t.quote_amount for t in buys)
    flagged = [t for t in sells if t.basis_is_incomplete]
    winners = [t for t in sells if t.realized_pnl_quote > 0]

    span = ""
    if trades:
        lo = min(t.timestamp for t in trades)
        hi = max(t.timestamp for t in trades)
        span = f"{_dur(hi - lo)} of history"

    lines = [
        "TRADER PROFILE (all four wallets netted as one entity)",
        "=" * 68,
        f"  wallets                 {len(wallets)}",
        f"  distinct tokens         {len(tokens)}",
        f"  buys / sells / exits    {len(buys)} / {len(sells)} / {len(exits)}",
        f"  total bought            {_fmt(spent, f' {unit}', 3)}",
        f"  realised PnL            {_fmt(realized, f' {unit}', 3)}",
        f"  sell win rate           {_pct(100.0 * len(winners) / len(sells)) if sells else 'n/a'}",
        f"  history span            {span}",
    ]
    if flagged:
        lines.append(
            f"  ! {len(flagged)} sells have incomplete cost basis "
            "(airdropped/bridged-in tokens); their PnL is a floor, not a fact."
        )
    transfers_out = [t for t in trades if t.kind == TRANSFER_OUT]
    if transfers_out:
        lines.append(
            f"  ! {len(transfers_out)} outbound transfers (CEX/bridge) are excluded "
            "from sell statistics -- they are not market exits."
        )
    return "\n".join(lines)


def render_pump(summary: Dict) -> str:
    lines = ["", "POST-SELL CONTINUATION -- does it keep pumping after he exits?",
             "=" * 68,
             f"  exits analysed: {summary['n_exits']}", ""]
    for label, block in summary["horizons"].items():
        lines.append(f"  horizon {label}  (sold the top: "
                     f"{_pct(block['sold_the_top_pct'])} of exits)")
        rows = []
        for _, row in sorted(block["tiers"].items()):
            ci = row["paper_ci"]
            ci_text = f"[{ci[0]:.0f}-{ci[1]:.0f}]" if ci else "-"
            rows.append([
                f">= +{row['tier_pct']:.0f}%",
                _pct(row["paper_pct"]),
                ci_text,
                _pct(row["realizable_pct"]),
                str(row["paper_n"]),
            ])
        lines.append(_table(
            ["   tier", "paper", "95% CI", "achievable", "n"], rows))
        paper, realiz = block["paper_return"], block["realizable_return"]
        close = block["close_return"]
        lines.append(
            f"    peak move  median {_ret(paper['median'])}  "
            f"p75 {_ret(paper['p75'])}  p90 {_ret(paper['p90'])}")
        lines.append(
            f"    achievable median {_ret(realiz['median'])}  "
            f"p75 {_ret(realiz['p75'])}")
        lines.append(
            f"    price at horizon median {_ret(close['median'])}  "
            f"| median time to peak {_dur(block['seconds_to_peak']['median'])}")
        lines.append("")
    lines.append("  paper      = best price printed after his sell (not necessarily")
    lines.append("               tradeable -- a wick on no volume counts here)")
    lines.append("  achievable = best VWAP you could have sold HIS size into,")
    lines.append("               capped at the configured share of real volume")
    return "\n".join(lines)


def render_breakdown(outcomes: Sequence[ExitOutcome], label: str,
                     horizon: str = "1h", unit: str = "ETH") -> str:
    if not outcomes:
        return ""
    keyfn = {"size": size_bucket, "hold": hold_bucket,
             "exit": lambda o: "full exit" if o.is_full_exit else "partial"}[label]
    buckets = segment(outcomes, keyfn)
    rows = []
    for name, group in sorted(buckets.items()):
        sub = summarize(group, horizons=[(horizon, 3600)], tiers=[0.0, 0.5])
        block = sub["horizons"][horizon]
        rows.append([
            name, str(len(group)),
            _pct(block["tiers"]["0.00"]["paper_pct"]),
            _pct(block["tiers"]["0.50"]["paper_pct"]),
            _ret(block["paper_return"]["median"]),
        ])
    title = {"size": f"by exit size ({unit})", "hold": "by holding period",
             "exit": "full vs partial exit"}[label]
    return "\n".join([
        f"  {title} -- {horizon} window",
        _table(["   bucket", "n", "pumped", ">= +50%", "median peak"], rows), ""])


def render_backtest(results: Dict[str, Dict], unit: str = "ETH") -> str:
    lines = ["", "COPY-TRADING BACKTEST", "=" * 68]
    rows = []
    for model in MODELS:
        block = results.get(model)
        if not block:
            continue
        m = block["metrics"]
        if not m.get("n"):
            rows.append([model, "0", "-", "-", "-", "-", "-", "-"])
            continue
        rows.append([
            model, str(m["n"]),
            _fmt(m["net_pnl_eth"], f" {unit}", 3),
            _pct(m["return_on_deployed_pct"]),
            _pct(m["win_rate_pct"]),
            _fmt(m["profit_factor"], "", 2) if m["profit_factor"] else "inf",
            _fmt(m["max_drawdown_eth"], f" {unit}", 3),
            _dur(m["median_hold_seconds"]),
        ])
    lines.append(_table(
        ["model", "n", f"net PnL ({unit})", "on deployed", "win%", "PF",
         f"max DD ({unit})", "med hold"],
        rows))

    skipped = {m: len(results[m]["skipped"]) for m in results if m in results}
    if any(skipped.values()):
        lines.append("")
        lines.append("  signals skipped (unfillable or over the concurrency cap): "
                     + ", ".join(f"{m}={n}" for m, n in skipped.items()))
    return "\n".join(lines)


def render_exit_reasons(results: Dict[str, Dict]) -> str:
    lines = ["", "  exit reason mix"]
    rows = []
    for model in MODELS:
        block = results.get(model)
        if not block or not block["positions"]:
            continue
        counts: Dict[str, int] = {}
        for pos in block["positions"]:
            for leg in pos.legs:
                counts[leg.reason] = counts.get(leg.reason, 0) + 1
            if pos.unsold_tokens > DUST and not pos.legs:
                counts["stuck_no_liquidity"] = counts.get("stuck_no_liquidity", 0) + 1
        rows.append([model, ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))])
    return "\n".join(lines + [_table(["model", "legs"], rows)]) if rows else ""


def to_json(profile_trades: Sequence[Trade], summary: Dict,
            results: Dict[str, Dict]) -> str:
    payload = {
        "summary": summary,
        "backtest": {
            model: {
                "metrics": {k: v for k, v in block["metrics"].items()
                            if k != "equity_curve"},
                "equity_curve": block["metrics"].get("equity_curve", []),
                "positions": [
                    {
                        "token": p.token, "symbol": p.symbol,
                        "entry_ts": p.entry_ts, "exit_ts": p.exit_ts,
                        "entry_price": p.entry_price, "cost_eth": p.cost_eth,
                        "proceeds_eth": p.proceeds_eth, "pnl_eth": p.pnl_eth,
                        "roi": p.roi,
                        "legs": [{"ts": l.timestamp, "reason": l.reason,
                                  "price": l.price, "proceeds_eth": l.proceeds_eth}
                                 for l in p.legs],
                    } for p in block["positions"]
                ],
            } for model, block in results.items()
        },
        "trades": [
            {"tx": t.tx_hash, "ts": t.timestamp, "kind": t.kind,
             "token": t.token, "symbol": t.symbol, "amount": t.token_amount,
             "quote": t.quote_amount, "price": t.price,
             "pnl": t.realized_pnl_quote, "full_exit": t.is_full_exit,
             "basis_incomplete": t.basis_is_incomplete}
            for t in profile_trades
        ],
    }
    return json.dumps(payload, indent=2, default=str)
