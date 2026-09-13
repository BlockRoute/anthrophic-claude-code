"""Static configuration for Robinhood Chain (chain id 4663) wallet analysis.

Every value here is overridable from the CLI or a JSON config file so the
pipeline can be pointed at another Arbitrum-Orbit chain without code changes.
"""

from dataclasses import dataclass, field

CHAIN_ID = 4663
CHAIN_NAME = "robinhood"

# Official Blockscout instance (free, no key) and the Pro gateway (key required).
BLOCKSCOUT_BASE = "https://robinhoodchain.blockscout.com"
BLOCKSCOUT_PRO_BASE = "https://api.blockscout.com"
RPC_URL = "https://rpc.mainnet.chain.robinhood.com"

WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
NATIVE = "native"

# A "quote" asset is what a memecoin is priced in. Matching is by symbol first
# (robust when an address list is incomplete) with an explicit address override.
QUOTE_SYMBOLS = {"WETH", "ETH", "USDC", "USDT", "DAI", "USDC.E"}
QUOTE_ADDRESSES = {WETH, NATIVE}

# The four addresses under analysis. Treated as ONE trading entity: transfers
# between them are position moves, not trades, and must not be counted as either.
WALLETS = [
    "0x19373466ea82bf277ba0ad97566ec59b09ea2835",
    "0xd95beca5294b310997fca0e558c9fe37d3a9d83e",
    "0x730d68da4a199a8f10883ccac996d0cc464c07b6",
    "0x301168707b4740585ec80232ef020486f198cbf0",
]

# Post-sell measurement horizons, in seconds.
HORIZONS = [
    ("5m", 300),
    ("1h", 3600),
    ("4h", 14400),
    ("24h", 86400),
    ("7d", 604800),
]

# "Continued to pump" tiers, as fractional gain over the realised sell price.
PUMP_TIERS = [0.0, 0.25, 0.50, 1.00]


@dataclass
class Costs:
    """Execution frictions applied to every simulated fill."""

    gas_eth_per_swap: float = 0.00002  # Orbit L2 gas is cheap but not free
    swap_fee_bps: float = 30.0  # Uniswap v3 1% pools exist; 0.30% is the median
    slippage_bps: float = 75.0  # thin memecoin books; tune from your own fills
    latency_seconds: float = 2.0  # delay between his tx landing and yours

    def round_trip_bps(self) -> float:
        return 2.0 * (self.swap_fee_bps + self.slippage_bps)


@dataclass
class BacktestParams:
    """Copy-trading simulation knobs."""

    notional_eth: float = 0.25  # fixed size per copied entry
    max_concurrent: int = 8  # cap simultaneous open positions
    take_profit_mult: float = 2.0  # model B/C: exit at 2x entry
    stop_loss_pct: float = 0.45  # model B/C: exit at -45%
    trailing_stop_pct: float = 0.35  # model B/C: give back 35% from the peak
    scale_out_fraction: float = 0.5  # model C: fraction sold at his exit
    max_hold_seconds: int = 604800  # hard time stop at 7d
    participation_rate: float = 0.15  # you can be at most 15% of traded volume
    costs: Costs = field(default_factory=Costs)


@dataclass
class IngestParams:
    """Limits on how much history to pull."""

    max_pages_per_address: int = 200
    max_pages_per_token: int = 60
    page_size: int = 50
    request_timeout: float = 30.0
    max_retries: int = 5
    min_interval_seconds: float = 0.20  # client-side rate limit
    # Only build price history this far past a sell; bounds the token fetch.
    price_lookahead_seconds: int = 604800
