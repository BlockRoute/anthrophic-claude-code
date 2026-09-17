import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hoodtrack.models import Transfer
from hoodtrack.trades import (BUY, SELL, ROTATION_IN, ROTATION_OUT, TRANSFER_IN,
                              TRANSFER_OUT, build_trades)

W1 = "0x" + "a1" * 20
W2 = "0x" + "a2" * 20
POOL = "0x" + "bb" * 20
CEX = "0x" + "cc" * 20
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
MEME = "0x" + "dd" * 20
OTHER = "0x" + "ee" * 20
ENTITY = [W1, W2]


def tr(tx, ts, token, sender, receiver, amount, symbol="MEME", idx=0):
    return Transfer(tx, 1, ts, token, symbol, 18, sender, receiver, amount, idx)


class TestTradeReconstruction(unittest.TestCase):

    def test_buy_then_full_sell_pnl(self):
        transfers = [
            # buy 1000 MEME for 1 WETH
            tr("0x1", 1000, WETH, W1, POOL, 1.0, "WETH", 0),
            tr("0x1", 1000, MEME, POOL, W1, 1000.0, "MEME", 1),
            # sell 1000 MEME for 3 WETH
            tr("0x2", 2000, MEME, W1, POOL, 1000.0, "MEME", 0),
            tr("0x2", 2000, WETH, POOL, W1, 3.0, "WETH", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        buy = [t for t in trades if t.kind == BUY][0]
        sell = [t for t in trades if t.kind == SELL][0]
        self.assertAlmostEqual(buy.price, 0.001)
        self.assertAlmostEqual(sell.price, 0.003)
        self.assertAlmostEqual(sell.cost_basis_quote, 1.0)
        self.assertAlmostEqual(sell.realized_pnl_quote, 2.0)
        self.assertTrue(sell.is_full_exit)
        self.assertFalse(sell.basis_is_incomplete)
        self.assertAlmostEqual(sell.avg_hold_seconds, 1000.0)

    def test_transfer_between_own_wallets_is_not_a_trade(self):
        transfers = [tr("0x9", 500, MEME, W1, W2, 5000.0)]
        self.assertEqual(build_trades(transfers, ENTITY), [])

    def test_split_buy_across_wallets_nets_as_one_entity(self):
        # W1 pays the WETH, W2 receives the tokens: one entity, one buy.
        transfers = [
            tr("0x3", 100, WETH, W1, POOL, 2.0, "WETH", 0),
            tr("0x3", 100, MEME, POOL, W2, 500.0, "MEME", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].kind, BUY)
        self.assertAlmostEqual(trades[0].price, 0.004)

    def test_airdrop_then_sell_flags_incomplete_basis(self):
        transfers = [
            tr("0x4", 100, MEME, POOL, W1, 1000.0),          # airdrop, no quote leg
            tr("0x5", 200, MEME, W1, POOL, 1000.0, "MEME", 0),
            tr("0x5", 200, WETH, POOL, W1, 5.0, "WETH", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        self.assertEqual(trades[0].kind, TRANSFER_IN)
        sell = trades[1]
        self.assertEqual(sell.kind, SELL)
        self.assertTrue(sell.basis_is_incomplete)
        self.assertAlmostEqual(sell.cost_basis_quote, 0.0)

    def test_send_to_cex_is_not_a_sale(self):
        transfers = [
            tr("0x6", 100, WETH, W1, POOL, 1.0, "WETH", 0),
            tr("0x6", 100, MEME, POOL, W1, 1000.0, "MEME", 1),
            tr("0x7", 200, MEME, W1, CEX, 1000.0),  # withdrawal, no quote received
        ]
        trades = build_trades(transfers, ENTITY)
        out = trades[1]
        self.assertEqual(out.kind, TRANSFER_OUT)
        self.assertAlmostEqual(out.realized_pnl_quote, 0.0)
        self.assertFalse(out.is_full_exit)  # not an exit event for pump stats

    def test_partial_sell_is_not_full_exit(self):
        transfers = [
            tr("0xa", 100, WETH, W1, POOL, 1.0, "WETH", 0),
            tr("0xa", 100, MEME, POOL, W1, 1000.0, "MEME", 1),
            tr("0xb", 200, MEME, W1, POOL, 400.0, "MEME", 0),
            tr("0xb", 200, WETH, POOL, W1, 0.8, "WETH", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        sell = trades[1]
        self.assertFalse(sell.is_full_exit)
        self.assertAlmostEqual(sell.position_after, 600.0)
        self.assertAlmostEqual(sell.cost_basis_quote, 0.4)
        self.assertAlmostEqual(sell.realized_pnl_quote, 0.4)

    def test_rotation_directions(self):
        transfers = [
            tr("0xc", 100, MEME, W1, POOL, 1000.0, "MEME", 0),
            tr("0xc", 100, OTHER, POOL, W1, 50.0, "OTHER", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        kinds = {t.token: t.kind for t in trades}
        self.assertEqual(kinds[MEME], ROTATION_OUT)
        self.assertEqual(kinds[OTHER], ROTATION_IN)

    def test_fifo_ordering(self):
        transfers = [
            tr("0xd", 100, WETH, W1, POOL, 1.0, "WETH", 0),
            tr("0xd", 100, MEME, POOL, W1, 1000.0, "MEME", 1),   # basis 0.001
            tr("0xe", 200, WETH, W1, POOL, 4.0, "WETH", 0),
            tr("0xe", 200, MEME, POOL, W1, 1000.0, "MEME", 1),   # basis 0.004
            tr("0xf", 300, MEME, W1, POOL, 1000.0, "MEME", 0),   # sells the FIRST lot
            tr("0xf", 300, WETH, POOL, W1, 3.0, "WETH", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        sell = [t for t in trades if t.kind == SELL][0]
        self.assertAlmostEqual(sell.cost_basis_quote, 1.0)   # FIFO: cheap lot first
        self.assertAlmostEqual(sell.realized_pnl_quote, 2.0)

    def test_oversell_flags_incomplete_basis(self):
        transfers = [
            tr("0x10", 100, MEME, W1, POOL, 999.0, "MEME", 0),
            tr("0x10", 100, WETH, POOL, W1, 2.0, "WETH", 1),
        ]
        trades = build_trades(transfers, ENTITY)
        self.assertTrue(trades[0].basis_is_incomplete)

    def test_native_eth_buy_is_detected(self):
        transfers = [tr("0x11", 100, MEME, POOL, W1, 1000.0)]
        trades = build_trades(transfers, ENTITY, native_by_tx={"0x11": -1.5})
        self.assertEqual(trades[0].kind, BUY)
        self.assertAlmostEqual(trades[0].price, 0.0015)


if __name__ == "__main__":
    unittest.main(verbosity=2)
