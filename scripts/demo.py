"""End-to-end pipeline exercise on synthetic Blockscout-shaped data.

Runs the real ingest -> trades -> prices -> pump -> backtest code path against a
generated market whose ground truth we control, so the statistics can be checked
against a known answer. Also serves as a preview of the report format.

    python scripts/demo.py [--tokens 40] [--pump-prob 0.55] [--seed 7]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hoodtrack.backtest import run_backtest
from hoodtrack.config import BacktestParams, Costs, HORIZONS, PUMP_TIERS
from hoodtrack.ingest import parse_activity, traded_tokens
from hoodtrack.prices import build_series, infer_pools, looks_like_pool
from hoodtrack.pump import evaluate_exits, summarize
from hoodtrack.models import parse_transfer
from hoodtrack.report import (render_backtest, render_breakdown,
                              render_exit_reasons, render_profile, render_pump)
from hoodtrack.trades import build_trades

WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
WALLETS = [
    "0x19373466ea82bf277ba0ad97566ec59b09ea2835",
    "0xd95beca5294b310997fca0e558c9fe37d3a9d83e",
    "0x730d68da4a199a8f10883ccac996d0cc464c07b6",
    "0x301168707b4740585ec80232ef020486f198cbf0",
]
T0 = 1751328000  # 2026-07-01, Robinhood Chain mainnet launch


def iso(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000000Z")


def item(tx, ts, token, symbol, frm, to, amount, decimals=18, log_index=0, block=0):
    return {
        "block_number": block, "timestamp": iso(ts),
        "from": {"hash": frm}, "to": {"hash": to},
        "token": {"address": token, "symbol": symbol,
                  "decimals": str(decimals), "type": "ERC-20"},
        "total": {"decimals": str(decimals), "value": str(int(amount * 10 ** decimals))},
        "transaction_hash": tx, "log_index": log_index,
    }


class Market:
    """One token, one pool, a price path, and a crowd trading against it."""

    def __init__(self, idx, rng, pump_prob):
        self.rng = rng
        self.token = "0x%040x" % (0xDD00 + idx)
        self.pool = "0x%040x" % (0xBB00 + idx)
        self.symbol = f"MEME{idx}"
        self.start = T0 + rng.randint(0, 60 * 86400)
        self.price = 10 ** rng.uniform(-8, -5)
        self.pumps_after_exit = rng.random() < pump_prob
        self.items = []
        self.path = []

    def _print(self, ts, price, volume_base, trader, buying):
        """Emit both legs of a swap through the pool."""
        tx = "0x%064x" % self.rng.getrandbits(256)
        quote = volume_base * price
        if buying:
            legs = [(self.token, self.symbol, self.pool, trader, volume_base),
                    (WETH, "WETH", trader, self.pool, quote)]
        else:
            legs = [(self.token, self.symbol, trader, self.pool, volume_base),
                    (WETH, "WETH", self.pool, trader, quote)]
        for i, (tok, sym, frm, to, amt) in enumerate(legs):
            self.items.append(item(tx, ts, tok, sym, frm, to, amt, log_index=i))
        self.path.append((ts, price))
        return tx

    def generate(self, entity_wallet):
        rng = self.rng
        ts = self.start
        price = self.price
        crowd = ["0x%040x" % rng.getrandbits(150) for _ in range(12)]
        base_vol = 10 ** rng.uniform(7, 10)

        # --- accumulation before the entity arrives
        for _ in range(rng.randint(20, 60)):
            ts += rng.randint(20, 300)
            price *= 1.0 + rng.gauss(0.01, 0.06)
            self._print(ts, price, base_vol * rng.uniform(0.2, 2.0),
                        rng.choice(crowd), rng.random() < 0.55)

        # --- entity buys
        ts += rng.randint(30, 600)
        entry_price = price
        entity_size = base_vol * rng.uniform(0.05, 0.4)
        self._print(ts, entry_price, entity_size, entity_wallet, True)
        buy_ts = ts

        # --- run-up while he holds
        for _ in range(rng.randint(10, 80)):
            ts += rng.randint(20, 400)
            price *= 1.0 + rng.gauss(0.02, 0.09)
            self._print(ts, price, base_vol * rng.uniform(0.2, 2.5),
                        rng.choice(crowd), rng.random() < 0.6)

        # --- entity exits
        ts += rng.randint(30, 300)
        sell_price = price
        self._print(ts, sell_price, entity_size, entity_wallet, False)
        sell_ts = ts

        # --- what happens next is the thing we are measuring
        if self.pumps_after_exit:
            peak_mult = rng.choice([1.15, 1.4, 1.8, 2.5, 4.0])
            steps = rng.randint(10, 40)
            for i in range(steps):
                ts += rng.randint(20, 300)
                price = sell_price * (1 + (peak_mult - 1) * (i + 1) / steps)
                self._print(ts, price, base_vol * rng.uniform(0.3, 3.0),
                            rng.choice(crowd), True)
        # every memecoin eventually bleeds out
        for _ in range(rng.randint(30, 90)):
            ts += rng.randint(60, 900)
            price *= 1.0 - abs(rng.gauss(0.03, 0.05))
            self._print(ts, price, base_vol * rng.uniform(0.1, 1.2),
                        rng.choice(crowd), rng.random() < 0.35)

        return buy_ts, sell_ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int, default=40)
    ap.add_argument("--pump-prob", type=float, default=0.55)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    markets = []
    entity_items = []
    for i in range(args.tokens):
        wallet = WALLETS[i % len(WALLETS)]
        m = Market(i, rng, args.pump_prob)
        m.generate(wallet)
        markets.append(m)
        entity_items.extend([
            it for it in m.items
            if it["from"]["hash"] in WALLETS or it["to"]["hash"] in WALLETS
        ])

    print(f"synthetic market: {args.tokens} tokens, "
          f"{sum(len(m.items) for m in markets)} transfer legs, "
          f"ground-truth pump rate {args.pump_prob:.0%}\n")

    transfers, native_by_tx, gas_by_tx = parse_activity(
        {"transfers": entity_items, "transactions": []}, WALLETS)
    trades = build_trades(transfers, WALLETS, native_by_tx, gas_by_tx)

    # Price series via the same pool-inference path the live pipeline uses.
    series = {}
    for m in markets:
        parsed = [t for t in (parse_transfer(i) for i in m.items) if t]
        pools = infer_pools(parsed, m.token)
        sets = {p: [t for t in parsed if t.sender == p or t.receiver == p]
                for p in pools}
        sets = {p: v for p, v in sets.items() if looks_like_pool(v, m.token)}
        series[m.token] = build_series(m.token, sets)

    outcomes = evaluate_exits(trades, series, horizons=HORIZONS, participation=0.15)
    summary = summarize(outcomes, horizons=HORIZONS, tiers=PUMP_TIERS)
    params = BacktestParams(costs=Costs())
    results = run_backtest(trades, series, params)

    print(render_profile(trades, WALLETS))
    print(render_pump(summary))
    for label in ("exit", "size", "hold"):
        block = render_breakdown(outcomes, label)
        if block:
            print(block)
    print(render_backtest(results))
    print(render_exit_reasons(results))

    # --- self-check: recovered rate must track the ground truth
    measured = summary["horizons"]["7d"]["tiers"]["0.00"]["paper_pct"]
    print(f"\nself-check: ground truth {100 * args.pump_prob:.0f}% vs "
          f"recovered {measured:.0f}% at the 7d/any-gain cell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
