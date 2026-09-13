import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hoodtrack.config import BacktestParams, Costs
from hoodtrack.prices import PricePoint, PriceSeries
from hoodtrack.backtest import (MODEL_HOLD, MODEL_MIRROR, MODEL_SCALE_OUT,
                                entity_episodes, run_backtest)
from hoodtrack.trades import BUY, SELL, Trade

TOKEN = "0x" + "dd" * 20
W1 = "0x" + "a1" * 20

# price path: flat 1.0, spike to 3.0, fade to 2.0 where he sells,
# second spike to 5.0, then the token dies at 0.5
PATH = [(0, 1.0), (3, 1.0), (50, 1.2), (100, 3.0), (150, 2.5),
        (200, 2.0), (203, 2.0), (300, 5.0), (400, 0.5)]


def series():
    return PriceSeries(TOKEN, [PricePoint(ts, p, 1e9, p * 1e9, f"0x{ts}", "0xpool")
                               for ts, p in PATH])


def trade(kind, ts, amount, price, pos_before, pos_after, full_exit=False):
    t = Trade(tx_hash=f"0x{kind}{ts}", timestamp=ts, kind=kind, token=TOKEN,
              symbol="MEME", token_amount=amount, quote_amount=amount * price,
              quote_symbol="WETH", price=price, wallets=[W1])
    t.position_before, t.position_after = pos_before, pos_after
    t.is_full_exit = full_exit
    return t


def entity_trades():
    return [trade(BUY, 0, 1000.0, 1.0, 0.0, 1000.0),
            trade(SELL, 200, 1000.0, 2.0, 1000.0, 0.0, full_exit=True)]


def params():
    return BacktestParams(
        notional_eth=0.25, take_profit_mult=2.0, stop_loss_pct=0.45,
        trailing_stop_pct=0.35, scale_out_fraction=0.5,
        costs=Costs(gas_eth_per_swap=0.00002, swap_fee_bps=30.0,
                    slippage_bps=75.0, latency_seconds=2.0))


class TestBacktest(unittest.TestCase):

    def test_episode_pairing(self):
        eps = entity_episodes(entity_trades())
        self.assertEqual(len(eps), 1)
        buy, exits = eps[0]
        self.assertEqual(buy.kind, BUY)
        self.assertEqual(len(exits), 1)

    def test_all_models_produce_positions(self):
        res = run_backtest(entity_trades(), {TOKEN: series()}, params())
        for model in (MODEL_MIRROR, MODEL_HOLD, MODEL_SCALE_OUT):
            self.assertEqual(res[model]["metrics"]["n"], 1, model)

    def test_mirror_captures_his_exit_price(self):
        res = run_backtest(entity_trades(), {TOKEN: series()}, params())
        pos = res[MODEL_MIRROR]["positions"][0]
        self.assertEqual(pos.legs[-1].reason, "mirror")
        self.assertAlmostEqual(pos.legs[-1].price, 2.0, places=6)
        self.assertGreater(pos.pnl_eth, 0.0)
        self.assertAlmostEqual(pos.roi, 0.96, delta=0.05)

    def test_hold_beats_mirror_when_price_ran_further(self):
        res = run_backtest(entity_trades(), {TOKEN: series()}, params())
        self.assertGreater(res[MODEL_HOLD]["metrics"]["net_pnl_eth"],
                           res[MODEL_MIRROR]["metrics"]["net_pnl_eth"])
        self.assertEqual(res[MODEL_HOLD]["positions"][0].legs[-1].reason, "take_profit")

    def test_scale_out_has_two_legs(self):
        res = run_backtest(entity_trades(), {TOKEN: series()}, params())
        pos = res[MODEL_SCALE_OUT]["positions"][0]
        self.assertEqual(pos.legs[0].reason, "scale_out")
        self.assertGreaterEqual(len(pos.legs), 2)

    def test_costs_reduce_pnl(self):
        free = params()
        free.costs = Costs(gas_eth_per_swap=0.0, swap_fee_bps=0.0,
                           slippage_bps=0.0, latency_seconds=2.0)
        with_costs = run_backtest(entity_trades(), {TOKEN: series()}, params())
        without = run_backtest(entity_trades(), {TOKEN: series()}, free)
        self.assertLess(with_costs[MODEL_MIRROR]["metrics"]["net_pnl_eth"],
                        without[MODEL_MIRROR]["metrics"]["net_pnl_eth"])

    def test_illiquid_token_entry_is_skipped(self):
        thin = PriceSeries(TOKEN, [PricePoint(0, 1.0, 0.0001, 0.0001, "0x0", "0xp"),
                                   PricePoint(3, 1.0, 0.0001, 0.0001, "0x3", "0xp")])
        res = run_backtest(entity_trades(), {TOKEN: thin}, params())
        self.assertEqual(res[MODEL_MIRROR]["metrics"]["n"], 0)
        self.assertTrue(res[MODEL_MIRROR]["skipped"])

    def test_stop_loss_fires(self):
        crash = PriceSeries(TOKEN, [PricePoint(ts, p, 1e9, p * 1e9, f"0x{ts}", "0xp")
                                    for ts, p in [(0, 1.0), (3, 1.0), (60, 0.4),
                                                  (70, 0.38)]])
        res = run_backtest(entity_trades(), {TOKEN: crash}, params())
        pos = res[MODEL_HOLD]["positions"][0]
        self.assertEqual(pos.legs[-1].reason, "stop_loss")
        self.assertLess(pos.pnl_eth, 0.0)

    def test_position_with_no_liquidity_after_trigger_is_stuck(self):
        """If trading stops dead, the stop cannot fill and the position is a
        total loss with tokens still held. It must not be booked as a clean exit."""
        rug = PriceSeries(TOKEN, [PricePoint(ts, p, 1e9, p * 1e9, f"0x{ts}", "0xp")
                                  for ts, p in [(0, 1.0), (3, 1.0), (60, 0.4)]])
        res = run_backtest(entity_trades(), {TOKEN: rug}, params())
        pos = res[MODEL_HOLD]["positions"][0]
        self.assertEqual(pos.legs, [])
        self.assertGreater(pos.unsold_tokens, 0.0)
        self.assertAlmostEqual(pos.proceeds_eth, 0.0)
        self.assertLess(pos.pnl_eth, 0.0)

    def test_metrics_fields(self):
        res = run_backtest(entity_trades(), {TOKEN: series()}, params())
        m = res[MODEL_MIRROR]["metrics"]
        for field in ("net_pnl_eth", "win_rate_pct", "max_drawdown_eth",
                      "profit_factor", "median_roi_pct", "equity_curve"):
            self.assertIn(field, m)
        self.assertLessEqual(m["max_drawdown_eth"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
