# hoodtrack

Wallet forensics and copy-trade backtesting for **Robinhood Chain** (chain id
4663, Arbitrum Orbit L2, Uniswap v2/v3/v4).

Answers two questions about a set of wallets belonging to one trader:

1. **After he sells, does the token keep pumping?** — and how much of that
   continuation you could actually have captured.
2. **Is copying him profitable?** — under three different exit rules, net of
   gas, fees, slippage, latency and liquidity limits.

Pure standard library. Python 3.9+. No `pip install`.

## Quickstart

```bash
python -m hoodtrack run -v --json out/report.json
```

Defaults to the four wallets in `config.py`, treated as one entity. To point it
elsewhere:

```bash
python -m hoodtrack run --wallet-file wallets.txt --max-tokens 100
```

Everything fetched is cached under `data/cache/`, so re-running the analysis
with different assumptions costs nothing:

```bash
python -m hoodtrack run --take-profit 3.0 --trailing-stop 0.25 --latency 5
```

Add `--refresh` to re-fetch. A [Blockscout API key](https://dev.blockscout.com)
raises rate limits: `--api-key` or `BLOCKSCOUT_API_KEY`.

Preview the report format without touching the network:

```bash
python scripts/demo.py --tokens 40 --pump-prob 0.55
```

## How it works

**Trades are reconstructed from transfers, not from decoded router calls.**
For each transaction we compute the *entity's* net token delta: a non-quote
token up and a quote asset down is a buy, whatever contract executed it. This
survives aggregators, v4 hooks and DEXes that do not exist yet. Because all four
wallets are netted as one entity, a transfer between them correctly nets to zero
instead of being booked as a sell plus a buy.

**Prices are rebuilt from pool flow.** For any AMM, a swap moves the base and
quote tokens through the pool in opposite directions in one transaction, so
`price = |pool quote delta| / |pool base delta|`. Identical for v2, v3 and v4.
This also yields per-print volume, which is what makes the next part possible.

**Every return is reported twice:**

| | meaning |
|---|---|
| `paper` | best price printed in the window — includes wicks on no volume |
| `achievable` | best VWAP you could have sold **his size** into, capped at `--participation` of each print's volume |

The gap between them is the difference between a backtest and a fill. A +400%
print on $80 of liquidity shows up in `paper` and correctly vanishes from
`achievable`.

## Exit models

| model | rule |
|---|---|
| `mirror` | sell the same fraction of your position he sells, when he sells it |
| `hold` | ignore his exits; run your own take-profit / stop / trailing stop |
| `scale_out` | sell `--scale-out` at his exit, let the rest ride on the `hold` rules |

Entry is identical in all three — you enter `--latency` seconds after he does,
filling at what the market actually offered — so the comparison isolates the
exit rule. Only his *first* buy of a token opens a position; later adds are
ignored so every model trades the same size on the same signals.

## Things it deliberately does not do

- **Sends to a CEX or bridge are not sales.** They remove the position without a
  price, and counting them as exits inflates both the pump stats and PnL.
- **Airdropped or bridged-in tokens have no cost basis.** Those sells are
  flagged `basis_is_incomplete` and their PnL is reported as a floor, not a
  fact. Same for selling more than we ever saw bought — truncated history is
  flagged rather than booked as pure profit.
- **A window with no prints is unobserved, not a 0% move.** It only becomes a
  real zero when the series proves the token was still being indexed and simply
  did not trade.
- **A position that cannot be sold is not a clean exit.** If the stop fires and
  no liquidity follows, the tokens stay stuck and the loss is total.

## Caveats that no amount of code fixes

Wallet clustering is an assumption, not a proof. Four addresses trading similar
tokens is suggestive; it is not evidence of one owner, and the entity netting is
wrong if it is wrong.

Past edge decays. A wallet worth copying is usually one that is early, and being
early is exactly the property that does not survive being followed. Size your
exposure on the assumption that the measured edge shrinks.

`--participation 0.15` is a guess until you calibrate it against your own fills.
Every achievable number scales with it.
