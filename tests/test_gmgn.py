import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hoodtrack.sources.gmgn import (Gmgn, parse_activity, series_from_kline,
                                    to_float, trades_from_activity)
from hoodtrack.pump import evaluate_exits
from hoodtrack.trades import BUY, SELL, TRANSFER_OUT

TOKEN = "0x" + "dd" * 20
W1 = "0x" + "a1" * 20


def act(kind, ts, amount, price, cost, tx="0xabc", wallet=W1):
    """An activity row in GMGN's documented shape (numbers as strings)."""
    return {
        "event_type": kind, "timestamp": ts, "tx_hash": tx,
        "wallet_address": wallet,
        "token": {"address": TOKEN, "symbol": "MEME", "total_supply": "1000000000"},
        "token_amount": str(amount), "price_usd": str(price),
        "cost_usd": str(cost), "gas_usd": "0.01",
    }


def candle(ms, o, h, l, c, volume, amount):
    return {"time": ms, "open": str(o), "high": str(h), "low": str(l),
            "close": str(c), "volume": str(volume), "amount": str(amount),
            "source": "uniswapv3"}


class FakeClient:
    """Stands in for JsonClient; records the queries it was given."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        return self.pages.pop(0)


class TestToFloat(unittest.TestCase):
    def test_string_numerics(self):
        self.assertEqual(to_float("0.0000082444906"), 0.0000082444906)
        self.assertEqual(to_float("12"), 12.0)

    def test_missing_and_garbage_default_to_zero(self):
        for bad in (None, "", "abc", [], {}):
            self.assertEqual(to_float(bad), 0.0)

    def test_nan_and_inf_rejected(self):
        self.assertEqual(to_float("nan"), 0.0)
        self.assertEqual(to_float("inf"), 0.0)
        self.assertEqual(to_float("-inf"), 0.0)


class TestActivityParsing(unittest.TestCase):

    def test_buy_row(self):
        t = parse_activity(act("buy", 1000, 5000, 0.002, 10.0))
        self.assertEqual(t.kind, BUY)
        self.assertEqual(t.token, TOKEN)
        self.assertAlmostEqual(t.token_amount, 5000.0)
        self.assertAlmostEqual(t.quote_amount, 10.0)
        self.assertAlmostEqual(t.price, 0.002)
        self.assertEqual(t.quote_symbol, "USD")

    def test_type_field_fallback_and_casing(self):
        row = act("buy", 1000, 1, 1, 1)
        del row["event_type"]
        row["type"] = "SELL"
        self.assertEqual(parse_activity(row).kind, SELL)

    def test_transfer_out_is_not_a_sale(self):
        self.assertEqual(parse_activity(act("transferOut", 1, 100, 1, 0)).kind,
                         TRANSFER_OUT)

    def test_zero_amount_liquidity_row_dropped(self):
        """Measured live on launchpads: add/remove rows with both amounts zero."""
        self.assertIsNone(parse_activity(act("remove", 1000, 0, 0, 0)))

    def test_unknown_event_type_dropped(self):
        self.assertIsNone(parse_activity(act("airdrop_claim", 1000, 1, 1, 1)))

    def test_price_derived_when_missing(self):
        row = act("buy", 1000, 4000, 0, 8.0)
        row["price_usd"] = ""
        self.assertAlmostEqual(parse_activity(row).price, 0.002)

    def test_quote_amount_fallback(self):
        row = act("sell", 1000, 100, 0.5, 0)
        row["cost_usd"] = "0"
        row["quote_amount"] = "50"
        self.assertAlmostEqual(parse_activity(row).quote_amount, 50.0)


class TestTradesFromActivity(unittest.TestCase):

    def test_dedup_across_wallets_and_fifo_pnl(self):
        rows = [
            act("buy", 1000, 1000, 0.001, 1.0, tx="0x1"),
            act("buy", 1000, 1000, 0.001, 1.0, tx="0x1"),  # same fill, other wallet page
            act("sell", 2000, 1000, 0.003, 3.0, tx="0x2"),
        ]
        trades = trades_from_activity(rows)
        self.assertEqual(len(trades), 2)
        sell = trades[1]
        self.assertAlmostEqual(sell.cost_basis_quote, 1.0)
        self.assertAlmostEqual(sell.realized_pnl_quote, 2.0)
        self.assertTrue(sell.is_full_exit)

    def test_rows_sorted_chronologically(self):
        rows = [act("sell", 2000, 500, 0.004, 2.0, tx="0x2"),
                act("buy", 1000, 500, 0.002, 1.0, tx="0x1")]
        trades = trades_from_activity(rows)
        self.assertEqual([t.kind for t in trades], [BUY, SELL])


class TestKline(unittest.TestCase):

    def test_millisecond_time_converted_to_seconds(self):
        s = series_from_kline(TOKEN, [candle(1767312000000, 1, 2, 0.9, 1.5, 300, 200)])
        self.assertEqual(s.points[0].timestamp, 1767312000)

    def test_unordered_candles_sorted(self):
        s = series_from_kline(TOKEN, [
            candle(2000000, 1, 1, 1, 1, 10, 10),
            candle(1000000, 1, 1, 1, 1, 10, 10),
        ])
        self.assertEqual([p.timestamp for p in s.points], [1000, 2000])

    def test_unusable_candles_dropped(self):
        rows = [candle(1000000, 1, 0, 1, 1, 5, 5),      # high missing
                candle(2000000, 1, 1, 1, "", 5, 5),     # close missing
                candle(3000000, 1, 2, 1, 1.5, 5, 5)]    # good
        self.assertEqual(len(series_from_kline(TOKEN, rows)), 1)

    def test_volume_base_derived_when_amount_absent(self):
        row = candle(1000000, 1, 1, 1, 2.0, 100, 0)
        s = series_from_kline(TOKEN, [row])
        self.assertAlmostEqual(s.points[0].volume_base, 50.0)

    def test_high_used_for_paper_but_not_for_fills(self):
        """The wick counts as paper upside; a fill still executes at the close."""
        s = series_from_kline(TOKEN, [
            candle(1000000, 1, 1, 1, 1.0, 1e6, 1e6),
            candle(2000000, 1, 5.0, 1, 1.10, 1e6, 1e6),  # spike to 5, closes at 1.10
        ])
        peak, _ts = s.max_in(999, 3000)
        self.assertAlmostEqual(peak, 5.0)                       # paper sees the wick
        vwap, frac, _ = s.fill_from(1500, 1000, participation=0.15)
        self.assertAlmostEqual(vwap, 1.10)                      # fill gets the close
        self.assertAlmostEqual(frac, 1.0)


class TestClient(unittest.TestCase):

    def test_auth_params_fresh_per_call(self):
        c = FakeClient([{"code": 0, "data": {"list": []}},
                        {"code": 0, "data": {"list": []}}])
        g = Gmgn(c, api_key="k")
        g.token_kline("robinhood", TOKEN)
        g.token_kline("robinhood", TOKEN)
        ids = [q["client_id"] for _u, q in c.calls]
        self.assertNotEqual(ids[0], ids[1])
        self.assertIn("timestamp", c.calls[0][1])

    def test_kline_query_shape(self):
        c = FakeClient([{"code": 0, "data": {"list": []}}])
        Gmgn(c).token_kline("robinhood", TOKEN, resolution="1m", start=10, end=20)
        _url, q = c.calls[0]
        self.assertEqual(q["chain"], "robinhood")
        self.assertEqual(q["address"], TOKEN)
        self.assertEqual(q["resolution"], "1m")
        self.assertEqual((q["from"], q["to"]), (10, 20))

    def test_activity_follows_cursor(self):
        c = FakeClient([
            {"code": 0, "data": {"activities": [act("buy", 3, 1, 1, 1)], "next": "c1"}},
            {"code": 0, "data": {"activities": [act("sell", 2, 1, 1, 1)], "next": None}},
        ])
        rows = list(Gmgn(c).wallet_activity("robinhood", W1))
        self.assertEqual(len(rows), 2)
        self.assertEqual(c.calls[1][1]["cursor"], "c1")

    def test_api_key_goes_in_header_not_query(self):
        """A key in the URL leaks into logs, caches and proxy records."""
        from hoodtrack.http import JsonClient
        c = JsonClient()
        Gmgn(c, api_key="secret123")
        self.assertEqual(c.extra_headers.get("X-APIKEY"), "secret123")
        self.assertIsNone(c.api_key)

    def test_works_without_header_support(self):
        """A client lacking extra_headers must not blow up on construction."""
        c = FakeClient([{"code": 0, "data": {"list": []}}])
        Gmgn(c, api_key="k").token_kline("robinhood", TOKEN)
        self.assertNotIn("apikey", c.calls[0][1])

    def test_api_error_code_raises(self):
        c = FakeClient([{"code": 429, "message": "rate limit exceeded"}])
        with self.assertRaises(RuntimeError) as ctx:
            Gmgn(c).token_kline("robinhood", TOKEN)
        self.assertIn("429", str(ctx.exception))


class TestEndToEndThroughPump(unittest.TestCase):

    def test_gmgn_data_flows_into_pump_stats(self):
        trades = trades_from_activity([
            act("buy", 1000, 1000, 0.001, 1.0, tx="0x1"),
            act("sell", 2000, 1000, 0.002, 2.0, tx="0x2"),
        ])
        series = series_from_kline(TOKEN, [
            candle(1000 * 1000, 0.001, 0.001, 0.001, 0.001, 1e6, 1e9),
            candle(2500 * 1000, 0.002, 0.006, 0.002, 0.004, 1e6, 1e9),
        ])
        outcomes = evaluate_exits(trades, {TOKEN: series},
                                  horizons=[("1h", 3600)], participation=0.15)
        self.assertEqual(len(outcomes), 1)
        h = outcomes[0].horizons["1h"]
        self.assertAlmostEqual(h.paper_return, 2.0)        # wick 0.006 vs sell 0.002
        self.assertAlmostEqual(h.realizable_return, 1.0)   # close 0.004 vs sell 0.002


if __name__ == "__main__":
    unittest.main(verbosity=2)
