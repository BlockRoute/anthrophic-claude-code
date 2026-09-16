"""Market-data / order adapters.

Two implementations share one interface:

  MockGMGN       deterministic synthetic data, no credentials, never writes on-chain
  GmgnCliAdapter shells out to `gmgn-cli` 1.3.9 for real data and real orders

Adapters never consult the LIVE/SHADOW mode or the master kill switch themselves.
The caller decides whether a write is permitted and passes that decision in as
`live_writes_allowed`; an adapter that receives False raises rather than signing.
"""

import hashlib
import json
import math
import random
import shlex
import subprocess
import time

CLI_TIMEOUT_SECONDS = 45


class AdapterError(RuntimeError):
    """Raised when an adapter cannot satisfy a request."""


class LiveWriteBlocked(RuntimeError):
    """Raised when an on-chain write is attempted without permission."""


# --- mock --------------------------------------------------------------------

_MOCK_WORDS = [
    "BONKAI", "SIGMA", "PEPEJET", "MOONLAB", "TURBODOG", "GIGACAT", "WIFHAT",
    "SOLRAT", "APEX9", "DEGENX", "BASEDOG", "FOMO404", "HODLR", "RUGME",
    "NYANZ", "VIBEZ", "ALPHAQ", "SNIPER", "CHADTO", "LAMBO",
]


class MockGMGN:
    """Synthetic adapter. Stable within a 30s bucket so polling looks coherent."""

    name = "MockGMGN"
    supports_live_orders = False

    def __init__(self, chain="sol", seed=None):
        self.chain = chain
        self._seed = seed

    def _rng(self, salt=""):
        bucket = self._seed if self._seed is not None else int(time.time() // 30)
        digest = hashlib.sha256(f"{self.chain}:{bucket}:{salt}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    def _address(self, symbol):
        digest = hashlib.sha256(f"{self.chain}:{symbol}".encode()).hexdigest()
        return digest[:44] if self.chain == "sol" else "0x" + digest[:40]

    def _live_price(self, address):
        """Smooth random walk so held positions actually show PnL movement."""
        base = self._rng(f"base:{address}").uniform(0.000001, 0.05)
        phase = int(hashlib.sha256(address.encode()).hexdigest()[:8], 16) % 1_000
        drift = 0.22 * math.sin(time.time() / 45.0 + phase) + 0.06 * math.sin(time.time() / 11.0 + phase)
        return round(max(1e-9, base * (1.0 + drift)), 9)

    def trending(self, command=None, limit=100):
        rng = self._rng("trending")
        rows = []
        for index in range(limit):
            word = _MOCK_WORDS[index % len(_MOCK_WORDS)]
            symbol = word if index < len(_MOCK_WORDS) else f"{word}{index // len(_MOCK_WORDS)}"
            r = self._rng(f"token:{symbol}")
            address = self._address(symbol)
            runner = r.random() < 0.10            # a handful of genuine movers per round
            if runner:
                momentum_5m = r.uniform(55, 180)
                buys, sells = r.randint(400, 1_600), r.randint(20, 180)
                liquidity = r.uniform(28_000, 480_000)
                volume_5m = liquidity * r.uniform(0.6, 2.4)
                holders = r.randint(400, 8_400)
            else:
                momentum_5m = r.uniform(-30, 70)
                buys, sells = r.randint(3, 700), r.randint(3, 700)
                liquidity = r.uniform(1_500, 300_000)
                volume_5m = liquidity * r.uniform(0.01, 0.9)
                holders = r.randint(12, 5_000)
            rows.append({
                "symbol": symbol,
                "name": f"{symbol.title()} Token",
                "address": address,
                "chain": self.chain,
                "price": self._live_price(address),
                "liquidity": round(liquidity, 2),
                "market_cap": round(liquidity * r.uniform(3, 40), 2),
                "volume_5m": round(volume_5m, 2),
                "volume_1h": round(volume_5m * r.uniform(3, 14), 2),
                "momentum_5m": round(momentum_5m, 2),
                "momentum_1h": round(momentum_5m * r.uniform(-0.8, 2.4), 2),
                "buy_count": buys,
                "sell_count": sells,
                "holders": holders,
                "top10_share": round(r.uniform(0.08, 0.94), 4),
                "age_minutes": r.randint(2, 4_300),
                "dev_address": self._address(f"dev:{symbol}"),
                "runner": runner,
            })
        rng.shuffle(rows)
        return rows

    def token_security(self, address, drift=0.0):
        """Skewed, not uniform: most trending tokens are clean-ish with a nasty tail,
        which is what makes the rug gate's pass rate look like the real thing."""
        r = self._rng(f"security:{address}")

        def skewed(clean_probability, low, high, clean_value=0.0):
            return clean_value if r.random() < clean_probability else round(r.uniform(low, high), 4)

        return {
            "address": address,
            "honeypot": r.random() < (0.11 + drift),
            "mintable": r.random() < (0.17 + drift),
            "renounced": r.random() > (0.28 + drift),
            "freezable": r.random() < 0.09,
            "buy_tax": skewed(0.60, 0.0, 0.15),
            "sell_tax": skewed(0.55, 0.0, 0.25),
            "lp_burned": r.random() > 0.35,
            "bundler_ratio": round(r.uniform(0, 0.25) if r.random() < 0.70 else r.uniform(0.25, 0.80), 4),
            "top10_share": round(min(0.99, (r.uniform(0.10, 0.55) if r.random() < 0.60
                                            else r.uniform(0.55, 0.95)) + drift), 4),
            "logo_hash": hashlib.sha256(f"logo:{r.randint(1, 60)}".encode()).hexdigest()[:16],
        }

    def token_price(self, address):
        return {
            "address": address,
            "price": self._live_price(address),
            "liquidity": round(self._rng(f"liq:{address}").uniform(1_000, 400_000), 2),
        }

    def created_tokens(self, dev_address, limit=50):
        r = self._rng(f"dev:{dev_address}")
        profile = r.random()
        if profile < 0.18:            # token factory
            count, graduate_rate = r.randint(400, 2_600), 0.01
        elif profile < 0.55:          # serial launcher
            count, graduate_rate = r.randint(8, 90), r.uniform(0.03, 0.2)
        else:                         # low-volume dev
            count, graduate_rate = r.randint(1, 12), r.uniform(0.1, 0.65)
        tokens = []
        shared_logo = hashlib.sha256(f"logo:{dev_address}".encode()).hexdigest()[:16]
        reskin = r.random() < 0.3
        for index in range(min(count, limit)):
            graduated = r.random() < graduate_rate
            tokens.append({
                "address": hashlib.sha256(f"{dev_address}:{index}".encode()).hexdigest()[:44],
                "symbol": f"T{index}",
                "graduated": graduated,
                "stuck_in_curve": not graduated,
                "logo_hash": shared_logo if reskin else hashlib.sha256(f"{dev_address}:{index}:logo".encode()).hexdigest()[:16],
                "created_at": time.time() - r.uniform(3_600, 90 * 86_400),
            })
        return {
            "dev_address": dev_address,
            "total_launches": count,
            "sampled": tokens,
            "exited": r.random() < 0.22,
        }

    def place_order(self, side, address, amount=None, percent=None,
                    live_writes_allowed=False, **kwargs):
        if live_writes_allowed:
            raise LiveWriteBlocked("MockGMGN cannot place real orders; switch to the gmgn-cli adapter")
        r = self._rng(f"order:{address}:{side}:{time.time()}")
        price = self.token_price(address)["price"]
        return {
            "order_id": "mock-" + hashlib.sha256(f"{address}{side}{time.time()}".encode()).hexdigest()[:12],
            "status": "filled",
            "side": side,
            "address": address,
            "amount": amount,
            "percent": percent,
            "fill_price": price,
            "tx_hash": None,
            "simulated": True,
            "slippage": round(r.uniform(0.002, 0.05), 4),
        }

    def order_status(self, order_id):
        return {"order_id": order_id, "status": "filled", "simulated": True}


# --- real CLI ----------------------------------------------------------------

class GmgnCliAdapter:
    """Shells out to `gmgn-cli`.

    Subcommand shapes are overridable because they are version-dependent; the
    defaults target gmgn-cli 1.3.9. Every invocation is returned/logged as an
    argv list so a LIVE order can be inspected before it is signed.
    """

    name = "gmgn-cli"
    supports_live_orders = True

    DEFAULT_COMMANDS = {
        "token_security": "gmgn-cli token security {address} --chain {chain} --json",
        "token_price": "gmgn-cli token price {address} --chain {chain} --json",
        "created_tokens": "gmgn-cli portfolio created-tokens {dev_address} --chain {chain} --limit {limit} --json",
        "buy": "gmgn-cli trade buy {address} --chain {chain} --amount {amount} --slippage {slippage} --json",
        "sell": "gmgn-cli trade sell {address} --chain {chain} --percent {percent} --slippage {slippage} --json",
        "order_status": "gmgn-cli trade status {order_id} --chain {chain} --json",
    }

    def __init__(self, chain="sol", api_key=None, signing_key_present=False, commands=None, runner=None):
        self.chain = chain
        self.api_key = api_key
        self.signing_key_present = signing_key_present
        self.commands = dict(self.DEFAULT_COMMANDS)
        if commands:
            self.commands.update({k: v for k, v in commands.items() if v})
        self._runner = runner or self._run_subprocess

    # -- plumbing

    def _run_subprocess(self, argv):
        try:
            completed = subprocess.run(
                argv, capture_output=True, text=True, timeout=CLI_TIMEOUT_SECONDS
            )
        except FileNotFoundError as exc:
            raise AdapterError("gmgn-cli is not installed or not on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise AdapterError(f"gmgn-cli timed out after {CLI_TIMEOUT_SECONDS}s") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:400]
            raise AdapterError(f"gmgn-cli exited {completed.returncode}: {detail}")
        return completed.stdout

    def _call(self, template_key, **fields):
        argv = self.argv(template_key, **fields)
        return self._parse(self._runner(argv), argv)

    def argv(self, template_key, **fields):
        template = self.commands[template_key]
        fields.setdefault("chain", self.chain)
        return shlex.split(template.format(**fields))

    @staticmethod
    def _parse(stdout, argv):
        stdout = (stdout or "").strip()
        if not stdout:
            raise AdapterError(f"gmgn-cli returned no output for: {' '.join(argv)}")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            for line in reversed(stdout.splitlines()):
                line = line.strip()
                if line.startswith("{") or line.startswith("["):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
        raise AdapterError(f"gmgn-cli output was not JSON for: {' '.join(argv)}")

    @staticmethod
    def _rows(payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "rows", "tokens", "result", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    for inner in ("rank", "list", "tokens", "items"):
                        if isinstance(value.get(inner), list):
                            return value[inner]
        return []

    # -- reads

    def trending(self, command, limit=100):
        argv = shlex.split(command)
        if argv[:3] != ["gmgn-cli", "market", "trending"]:
            raise AdapterError("trending command must start with: gmgn-cli market trending")
        if "--chain" not in argv:
            argv += ["--chain", self.chain]
        if "--json" not in argv:
            argv.append("--json")
        rows = self._rows(self._parse(self._runner(argv), argv))
        return [self._normalize_row(row) for row in rows[:limit]]

    def _normalize_row(self, row):
        def pick(*keys, default=None):
            for key in keys:
                if key in row and row[key] is not None:
                    return row[key]
            return default

        def number(*keys, default=0.0):
            try:
                return float(pick(*keys, default=default))
            except (TypeError, ValueError):
                return default

        return {
            "symbol": str(pick("symbol", "ticker", "token_symbol", default="?")).upper(),
            "name": str(pick("name", "token_name", default="")),
            "address": str(pick("address", "token_address", "mint", "contract", default="")),
            "chain": str(pick("chain", default=self.chain)),
            "price": number("price", "price_usd"),
            "liquidity": number("liquidity", "liquidity_usd", "lp"),
            "market_cap": number("market_cap", "marketcap", "mc", "fdv"),
            "volume_5m": number("volume_5m", "volume5m", "v5m"),
            "volume_1h": number("volume_1h", "volume1h", "v1h"),
            "momentum_5m": number("price_change_5m", "change_5m", "priceChange5m") * (100 if abs(number("price_change_5m", "change_5m", "priceChange5m")) <= 1 else 1),
            "momentum_1h": number("price_change_1h", "change_1h", "priceChange1h") * (100 if abs(number("price_change_1h", "change_1h", "priceChange1h")) <= 1 else 1),
            "buy_count": int(number("buys", "buy_count", "buys_5m")),
            "sell_count": int(number("sells", "sell_count", "sells_5m")),
            "holders": int(number("holder_count", "holders")),
            "top10_share": number("top_10_holder_rate", "top10_share"),
            "age_minutes": number("age_minutes") or max(0.0, (time.time() - number("created_at", "open_timestamp")) / 60 if number("created_at", "open_timestamp") else 0.0),
            "dev_address": str(pick("creator", "creator_address", "dev", "deployer", default="")),
            "raw": row,
        }

    def token_security(self, address, **_):
        payload = self._call("token_security", address=address)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}

        def flag(*keys):
            for key in keys:
                if key in data:
                    value = data[key]
                    if isinstance(value, str):
                        return value.strip().lower() in ("1", "true", "yes")
                    return bool(value)
            return False

        def number(*keys):
            for key in keys:
                if key in data:
                    try:
                        return float(data[key])
                    except (TypeError, ValueError):
                        continue
            return 0.0

        return {
            "address": address,
            "honeypot": flag("is_honeypot", "honeypot", "cannot_sell_all"),
            "mintable": flag("is_mintable", "mintable", "can_mint"),
            "renounced": flag("renounced", "renounced_ownership", "is_renounced"),
            "freezable": flag("is_freezable", "freezable", "transfer_pausable"),
            "buy_tax": number("buy_tax"),
            "sell_tax": number("sell_tax"),
            "lp_burned": flag("lp_burned", "is_lp_burned", "burn_status"),
            "bundler_ratio": number("bundler_ratio", "bundle_rate"),
            "top10_share": number("top_10_holder_rate", "top10_share"),
            "logo_hash": str(data.get("logo_hash") or data.get("logo") or ""),
            "raw": data,
        }

    def token_price(self, address):
        payload = self._call("token_price", address=address)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        try:
            price = float(data.get("price") or data.get("price_usd") or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        try:
            liquidity = float(data.get("liquidity") or 0.0)
        except (TypeError, ValueError):
            liquidity = 0.0
        return {"address": address, "price": price, "liquidity": liquidity}

    def created_tokens(self, dev_address, limit=50):
        payload = self._call("created_tokens", dev_address=dev_address, limit=limit)
        rows = self._rows(payload)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        sampled = []
        for row in rows:
            graduated = bool(row.get("graduated") or row.get("is_graduated") or row.get("complete"))
            sampled.append({
                "address": str(row.get("address") or row.get("token_address") or ""),
                "symbol": str(row.get("symbol") or ""),
                "graduated": graduated,
                "stuck_in_curve": not graduated,
                "logo_hash": str(row.get("logo_hash") or row.get("logo") or ""),
                "created_at": row.get("created_at") or row.get("open_timestamp") or 0,
            })
        total = data.get("total") if isinstance(data, dict) else None
        return {
            "dev_address": dev_address,
            "total_launches": int(total) if isinstance(total, (int, float)) else len(sampled),
            "sampled": sampled,
            "exited": bool(data.get("exited")) if isinstance(data, dict) else False,
        }

    # -- writes

    def preflight_order(self, side, address, amount=None, percent=None, slippage=0.15):
        """Return the exact argv a LIVE order would execute. Signs nothing."""
        if side == "buy":
            return self.argv("buy", address=address, amount=amount, slippage=slippage)
        return self.argv("sell", address=address, percent=percent, slippage=slippage)

    def place_order(self, side, address, amount=None, percent=None, slippage=0.15,
                    live_writes_allowed=False, **_):
        if not live_writes_allowed:
            raise LiveWriteBlocked(
                "on-chain write refused: LIVE mode and the LIVE_TRADING_DISABLED switch must both allow it"
            )
        if not self.signing_key_present:
            raise AdapterError("no signing key configured in ~/.config/gmgn/.env")
        argv = self.preflight_order(side, address, amount=amount, percent=percent, slippage=slippage)
        payload = self._parse(self._runner(argv), argv)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        return {
            "order_id": str(data.get("order_id") or data.get("id") or ""),
            "status": str(data.get("status") or "submitted"),
            "side": side,
            "address": address,
            "amount": amount,
            "percent": percent,
            "fill_price": data.get("fill_price") or data.get("price"),
            "tx_hash": data.get("tx_hash") or data.get("signature") or data.get("hash"),
            "simulated": False,
            "argv": argv,
            "raw": data,
        }

    def order_status(self, order_id):
        payload = self._call("order_status", order_id=order_id)
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        return {
            "order_id": order_id,
            "status": str(data.get("status") or "unknown"),
            "fill_price": data.get("fill_price") or data.get("price"),
            "tx_hash": data.get("tx_hash") or data.get("signature") or data.get("hash"),
            "simulated": False,
            "raw": data,
        }
