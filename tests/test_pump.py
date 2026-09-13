import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hoodtrack.prices import PricePoint, PriceSeries, series_from_pool_transfers
from hoodtrack.models import Transfer
from hoodtrack.pump import evaluate_exits, summarize, bootstrap_ci
from hoodtrack.trades import SELL, Trade

TOKEN = "0x" + "dd" * 20
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
POOL = "0x" + "bb" * 20
W1 = "0x" + "a1" * 20


def pt(ts, price, vol_base):
    return PricePoint(ts, price, vol_base, price * vol_base, f"0x{ts}", POOL)


def sell_trade(ts=1000, amount=1000.0, price=1.0):
    t = Trade(tx_hash="0xsell", timestamp=ts, kind=SELL, token=TOKEN, symbol="MEME",
              token_amount=amount, quote_amount=amount * price, quote_symbol="WETH",
              price=price, wallets=[W1])
    t.is_full_exit = True
    return t


class TestPumpStats(unittest.TestCase):

    def test_paper_vs_realizable_gap(self):
        """A high print on thin volume must not count as a capturable pump."""
        series = PriceSeries(TOKEN, [
            pt(1100, 2.0, 10.0),        # +100% but only 10 tokens traded
            pt(1200, 1.2, 100000.0),    # the only real liquidity
        ])
        outcomes = evaluate_exits([sell_trade()], {TOKEN: series},
                                  horizons=[("1h", 3600)], participation=0.15)
        self.assertEqual(len(outcomes), 1)
        h = outcomes[0].horizons["1h"]
        self.assertAlmostEqual(h.paper_return, 1.0, places=6)
        # 1.5 tokens at 2.0, the remaining 998.5 at 1.2
        self.assertAlmostEqual(h.realizable_return, 0.2012, places=4)
        self.assertAlmostEqual(h.filled_fraction, 1.0, places=6)

    def test_sold_the_top(self):
        series = PriceSeries(TOKEN, [pt(1100, 0.5, 1000.0), pt(1200, 0.4, 1000.0)])
        outcomes = evaluate_exits([sell_trade()], {TOKEN: series},
                                  horizons=[("1h", 3600)])
        self.assertTrue(outcomes[0].sold_the_top("1h"))
        self.assertLess(outcomes[0].horizons["1h"].paper_return, 0)

    def test_empty_window_is_unobserved_not_zero(self):
        """Series ends before the horizon: we must report None, not a 0% move."""
        series = PriceSeries(TOKEN, [pt(900, 1.0, 100.0)])
        outcomes = evaluate_exits([sell_trade(ts=1000)], {TOKEN: series},
                                  horizons=[("7d", 604800)])
        h = outcomes[0].horizons["7d"]
        self.assertIsNone(h.paper_return)
        self.assertEqual(h.prints_in_window, 0)

    def test_dead_token_after_sell_counts_as_zero(self):
        """Series extends past the horizon with no prints: token died, return 0."""
        series = PriceSeries(TOKEN, [pt(900, 1.0, 100.0), pt(99000, 0.9, 5.0)])
        outcomes = evaluate_exits([sell_trade(ts=1000)], {TOKEN: series},
                                  horizons=[("1h", 3600)])
        h = outcomes[0].horizons["1h"]
        self.assertEqual(h.paper_return, 0.0)

    def test_partial_fill_reported(self):
        """Position far larger than available volume cannot fully exit."""
        series = PriceSeries(TOKEN, [pt(1100, 3.0, 10.0)])
        outcomes = evaluate_exits([sell_trade(amount=100000.0)], {TOKEN: series},
                                  horizons=[("1h", 3600)], participation=0.15)
        h = outcomes[0].horizons["1h"]
        self.assertLess(h.filled_fraction, 0.001)
        self.assertAlmostEqual(h.paper_return, 2.0)

    def test_summary_tiers_and_ci(self):
        series_hot = PriceSeries(TOKEN, [pt(1100, 2.0, 1e9)])
        series_cold = PriceSeries(TOKEN, [pt(1100, 0.8, 1e9)])
        outs = []
        for i in range(6):
            s = series_hot if i < 4 else series_cold
            outs += evaluate_exits([sell_trade(ts=1000)], {TOKEN: s},
                                   horizons=[("1h", 3600)])
        rep = summarize(outs, horizons=[("1h", 3600)], tiers=[0.0, 0.5])
        row0 = rep["horizons"]["1h"]["tiers"]["0.00"]
        row50 = rep["horizons"]["1h"]["tiers"]["0.50"]
        self.assertAlmostEqual(row0["paper_pct"], 100.0 * 4 / 6)
        self.assertAlmostEqual(row50["paper_pct"], 100.0 * 4 / 6)
        self.assertIsNotNone(row0["paper_ci"])
        self.assertEqual(rep["horizons"]["1h"]["sold_the_top_pct"], 100.0 * 2 / 6)

    def test_bootstrap_ci_small_n_returns_none(self):
        self.assertIsNone(bootstrap_ci([True, False]))

    def test_price_series_from_pool_transfers(self):
        """Pool-side pairing must yield price and reject liquidity adds."""
        swap = [
            Transfer("0x1", 1, 100, TOKEN, "MEME", 18, POOL, W1, 1000.0, 0),
            Transfer("0x1", 1, 100, WETH, "WETH", 18, W1, POOL, 2.0, 1),
        ]
        add_liq = [  # both legs INTO the pool: not a trade
            Transfer("0x2", 1, 200, TOKEN, "MEME", 18, W1, POOL, 500.0, 0),
            Transfer("0x2", 1, 200, WETH, "WETH", 18, W1, POOL, 1.0, 1),
        ]
        pts = series_from_pool_transfers(POOL, TOKEN, swap + add_liq)
        self.assertEqual(len(pts), 1)
        self.assertAlmostEqual(pts[0].price, 0.002)
        self.assertAlmostEqual(pts[0].volume_base, 1000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
