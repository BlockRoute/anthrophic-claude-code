"""Command line entry point.

    python -m hoodtrack run                  # ingest + analyse, cached
    python -m hoodtrack run --refresh        # ignore the cache
    python -m hoodtrack run --json out/report.json
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List

from .backtest import run_backtest
from .config import (BLOCKSCOUT_BASE, BacktestParams, Costs, HORIZONS,
                     IngestParams, PUMP_TIERS, WALLETS)
from .http import JsonClient
from .ingest import (Cache, fetch_entity_activity, fetch_gmgn_activity,
                     fetch_gmgn_series, fetch_price_series, kline_windows,
                     parse_activity, price_windows, traded_tokens)
from .pump import evaluate_exits, summarize
from .report import (render_backtest, render_breakdown, render_exit_reasons,
                     render_profile, render_pump, to_json)
from .sources import Blockscout
from .trades import build_trades

log = logging.getLogger("hoodtrack")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hoodtrack", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["run", "ingest", "analyze"], nargs="?",
                   default="run")
    p.add_argument("--wallets", nargs="*", default=WALLETS,
                   help="addresses to treat as one entity")
    p.add_argument("--wallet-file", help="file with one address per line")
    p.add_argument("--source", choices=["blockscout", "gmgn"], default="blockscout",
                   help="blockscout reconstructs trades from transfers (quote-asset "
                        "denominated); gmgn uses pre-classified activity and klines "
                        "(USD denominated)")
    p.add_argument("--chain", default="robinhood", help="GMGN chain id")
    p.add_argument("--resolution", default="1m",
                   choices=["30s", "1m", "5m", "15m", "1h", "4h", "1d"],
                   help="GMGN kline resolution; bounds how tightly short "
                        "post-sell horizons can be measured")
    p.add_argument("--gmgn-key", default=os.environ.get("GMGN_API_KEY"))
    p.add_argument("--base-url", default=BLOCKSCOUT_BASE)
    p.add_argument("--api-key", default=os.environ.get("BLOCKSCOUT_API_KEY"))
    p.add_argument("--cache-dir", default="data/cache")
    p.add_argument("--refresh", action="store_true", help="bypass the cache")
    p.add_argument("--json", dest="json_out", help="write the full report as JSON")
    p.add_argument("--max-tokens", type=int, default=0,
                   help="only analyse the N most-traded tokens (0 = all)")

    g = p.add_argument_group("execution assumptions")
    g.add_argument("--notional", type=float, default=0.25,
                   help="ETH deployed per copied entry")
    g.add_argument("--latency", type=float, default=2.0,
                   help="seconds between his fill and yours")
    g.add_argument("--slippage-bps", type=float, default=75.0)
    g.add_argument("--fee-bps", type=float, default=30.0)
    g.add_argument("--gas-eth", type=float, default=0.00002)
    g.add_argument("--participation", type=float, default=0.15,
                   help="max share of traded volume you can be")
    g.add_argument("--max-concurrent", type=int, default=8)

    e = p.add_argument_group("exit rules (hold / scale_out models)")
    e.add_argument("--take-profit", type=float, default=2.0, help="multiple of entry")
    e.add_argument("--stop-loss", type=float, default=0.45, help="fraction below entry")
    e.add_argument("--trailing-stop", type=float, default=0.35)
    e.add_argument("--scale-out", type=float, default=0.5)
    e.add_argument("--max-hold", type=int, default=604800, help="seconds")

    p.add_argument("-v", "--verbose", action="store_true")
    return p


def resolve_wallets(args) -> List[str]:
    if args.wallet_file:
        with open(args.wallet_file) as fh:
            return [ln.strip().lower() for ln in fh
                    if ln.strip() and not ln.startswith("#")]
    return [w.lower() for w in args.wallets]


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s")

    wallets = resolve_wallets(args)
    if not wallets:
        print("no wallets given", file=sys.stderr)
        return 2

    ingest_params = IngestParams()
    client = JsonClient(timeout=ingest_params.request_timeout,
                        max_retries=ingest_params.max_retries,
                        min_interval=ingest_params.min_interval_seconds,
                        api_key=args.api_key)
    explorer = Blockscout(args.base_url, client,
                          max_pages=ingest_params.max_pages_per_address)
    cache = Cache(args.cache_dir)

    unit = "USD" if args.source == "gmgn" else "ETH"
    gmgn = None

    if args.source == "gmgn":
        from .sources.gmgn import GMGN_BASE, Gmgn, trades_from_activity
        if not args.gmgn_key:
            print("--gmgn-key (or GMGN_API_KEY) is required for --source gmgn",
                  file=sys.stderr)
            return 2
        # GMGN rate-limits hard and extends the ban on every request sent
        # during a cooldown, so stay strictly under 1 request/second.
        gmgn_client = JsonClient(timeout=ingest_params.request_timeout,
                                 max_retries=ingest_params.max_retries,
                                 min_interval=1.05)
        gmgn = Gmgn(gmgn_client, GMGN_BASE, api_key=args.gmgn_key)

        print(f"entity: {len(wallets)} wallets on GMGN chain {args.chain}")
        rows = fetch_gmgn_activity(gmgn, args.chain, wallets, cache,
                                   ingest_params, refresh=args.refresh)
        print(f"fetched {len(rows)} activity rows")
        if not rows:
            print("\nNo activity returned for these wallets.\n"
                  "Check --chain and that the addresses are correct.", file=sys.stderr)
            return 1
        trades = trades_from_activity(rows, args.chain)
        print(f"normalised {len(trades)} trades")
        if args.command == "ingest":
            return 0
        tokens = sorted({t.token for t in trades})
    else:
        print(f"entity: {len(wallets)} wallets on {args.base_url}")
        raw = fetch_entity_activity(explorer, wallets, cache, ingest_params,
                                    refresh=args.refresh)
        transfers, native_by_tx, gas_by_tx = parse_activity(raw, wallets)
        print(f"parsed {len(transfers)} token transfers, "
              f"{len(native_by_tx)} native flows")
        if not transfers:
            print("\nNo token transfers found for these wallets on this chain.\n"
                  "Check --base-url and that the addresses are correct.",
                  file=sys.stderr)
            return 1

        trades = build_trades(transfers, wallets, native_by_tx, gas_by_tx)
        print(f"reconstructed {len(trades)} trades")
        if args.command == "ingest":
            return 0
        tokens = traded_tokens(transfers)
    if args.max_tokens:
        volume = {}
        for t in trades:
            volume[t.token] = volume.get(t.token, 0.0) + t.quote_amount
        tokens = sorted(tokens, key=lambda tk: -volume.get(tk, 0.0))[:args.max_tokens]
    print(f"building price history for {len(tokens)} tokens "
          "(this is the slow part; results are cached)")

    def progress(i, total, token):
        print(f"  [{i}/{total}] {token}", end="\r", flush=True)

    if args.source == "gmgn":
        series = fetch_gmgn_series(
            gmgn, args.chain, tokens, cache, ingest_params,
            resolution=args.resolution,
            windows=kline_windows(trades, ingest_params.price_lookahead_seconds),
            refresh=args.refresh, progress=progress)
    else:
        series = fetch_price_series(
            explorer, tokens, cache, ingest_params,
            window_by_token=price_windows(trades,
                                          ingest_params.price_lookahead_seconds),
            refresh=args.refresh, progress=progress)
    print(" " * 70, end="\r")

    outcomes = evaluate_exits(trades, series, horizons=HORIZONS,
                              participation=args.participation)
    summary = summarize(outcomes, horizons=HORIZONS, tiers=PUMP_TIERS)

    params = BacktestParams(
        notional_eth=args.notional, max_concurrent=args.max_concurrent,
        take_profit_mult=args.take_profit, stop_loss_pct=args.stop_loss,
        trailing_stop_pct=args.trailing_stop, scale_out_fraction=args.scale_out,
        max_hold_seconds=args.max_hold, participation_rate=args.participation,
        costs=Costs(gas_eth_per_swap=args.gas_eth, swap_fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps, latency_seconds=args.latency))
    results = run_backtest(trades, series, params)

    print()
    print(render_profile(trades, wallets, unit=unit))
    print(render_pump(summary))
    for label in ("exit", "size", "hold"):
        block = render_breakdown(outcomes, label, unit=unit)
        if block:
            print(block)
    print(render_backtest(results, unit=unit))
    print(render_exit_reasons(results))

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as fh:
            fh.write(to_json(trades, summary, results))
        print(f"\nfull report written to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
