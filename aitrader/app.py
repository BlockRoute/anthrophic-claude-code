"""GMGN AI Trader (local) — FastAPI backend + single-page dashboard.

The machine screens, the human presses to trade.

    LIVE_TRADING_DISABLED = True  seals every on-chain write, whatever the UI says.

Set it to False only when you have verified the gmgn-cli order commands against
your installed CLI (GET /api/preflight prints the exact argv that would run).
Binds to 127.0.0.1 only.
"""

import os
import threading
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import positions as positions_mod
import risk
import store
from adapters import AdapterError, GmgnCliAdapter, LiveWriteBlocked, MockGMGN
from pipeline import THRESHOLDS, screen

# --- master safety switch ----------------------------------------------------
# True  -> buys/sells are paper fills only; no signing key is ever used.
# False -> LIVE mode is permitted to submit real, irreversible on-chain orders.
LIVE_TRADING_DISABLED = True

PUBLIC_DEMO = os.environ.get("PUBLIC_DEMO") == "1"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
TRENDING_TTL_SECONDS = 3.0
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="GMGN AI Trader (local)", docs_url=None, redoc_url=None)

_state_lock = threading.Lock()
_mode = "SHADOW"                       # resets to SHADOW on every restart, by design
_adapters = {}                         # chain -> adapter instance
_trending_cache = {}                   # chain -> (expires_at, rows)
_dev_cache = {}                        # dev_address -> evaluation
_events = []                           # ring buffer of UI log lines
_last_round = {}                       # chain -> {candidates, rejected, funnel}
_positions = store.load_positions()


def log_event(level, text):
    with _state_lock:
        _events.append({"ts": time.time(), "level": level, "text": text})
        del _events[:-300]


def validate_chain(chain):
    chain = (chain or "sol").lower()
    if chain not in store.CHAINS:
        raise ValueError(f"unsupported chain: {chain}")
    return chain


# --- adapter wiring ----------------------------------------------------------

def adapter_choice():
    return store.read_env().get("GMGN_ADAPTER", "mock").lower()


def get_adapter(chain):
    """One cached adapter per chain — same credentials, different --chain."""
    chain = validate_chain(chain)
    env = store.read_env()
    choice = env.get("GMGN_ADAPTER", "mock").lower()
    key = (chain, choice, bool(env.get("GMGN_API_KEY")), bool(env.get("GMGN_PRIVATE_KEY")))
    with _state_lock:
        cached = _adapters.get(chain)
        if cached and cached[0] == key:
            return cached[1]
        if choice == "cli":
            adapter = GmgnCliAdapter(
                chain=chain,
                api_key=env.get("GMGN_API_KEY"),
                signing_key_present=bool(env.get("GMGN_PRIVATE_KEY")),
                commands={
                    "buy": env.get("GMGN_BUY_CMD"),
                    "sell": env.get("GMGN_SELL_CMD"),
                    "order_status": env.get("GMGN_STATUS_CMD"),
                },
            )
        else:
            adapter = MockGMGN(chain=chain)
        _adapters[chain] = (key, adapter)
        return adapter


def live_writes_allowed(adapter):
    """The only place that decides whether a real order may be signed."""
    if LIVE_TRADING_DISABLED or PUBLIC_DEMO:
        return False
    return _mode == "LIVE" and getattr(adapter, "supports_live_orders", False)


def block_reason(adapter):
    if PUBLIC_DEMO:
        return "PUBLIC_DEMO=1: read-only"
    if LIVE_TRADING_DISABLED:
        return "LIVE_TRADING_DISABLED is True in app.py"
    if _mode != "LIVE":
        return "SHADOW mode"
    if not getattr(adapter, "supports_live_orders", False):
        return "MockGMGN adapter cannot place real orders"
    return ""


# --- request models ----------------------------------------------------------

class ConfigBody(BaseModel):
    api_key: str | None = None
    private_key: str | None = None
    adapter: str | None = None
    buy_cmd: str | None = None
    sell_cmd: str | None = None


class ModeBody(BaseModel):
    mode: str
    confirm: bool = False


class SettingsBody(BaseModel):
    chain: str = "sol"
    command: str | None = None
    reset: bool = False


class RunBody(BaseModel):
    chain: str = "sol"


class BuyBody(BaseModel):
    chain: str = "sol"
    address: str
    amount: float = Field(gt=0)
    confirm: bool = False


class PositionBody(BaseModel):
    key: str
    percent: float = 100.0


# --- serialisation -----------------------------------------------------------

def status_payload():
    env = store.read_env()
    adapter = get_adapter("sol")
    return {
        "adapter": getattr(adapter, "name", "unknown"),
        "adapter_choice": adapter_choice(),
        "mode": _mode,
        "live_trading_disabled": LIVE_TRADING_DISABLED,
        "public_demo": PUBLIC_DEMO,
        "api_key_present": bool(env.get("GMGN_API_KEY")),
        "signing_key_present": bool(env.get("GMGN_PRIVATE_KEY")),
        "trading_locked": not live_writes_allowed(adapter),
        "lock_reason": block_reason(adapter),
        "chains": list(store.CHAINS),
        "thresholds": THRESHOLDS,
        "limits": risk.LIMITS,
        "env_path": str(store.ENV_PATH),
    }


def public_positions():
    if PUBLIC_DEMO:
        return {}
    return _positions


def round_payload(chain):
    snapshot = _last_round.get(chain, {"candidates": [], "rejected": [], "funnel": {}})
    return {
        "chain": chain,
        "candidates": snapshot["candidates"],
        "rejected": snapshot["rejected"][:60],
        "funnel": snapshot["funnel"],
        "positions": list(public_positions().values()),
        "risk": risk.summary(public_positions()),
        "status": status_payload(),
        "events": _events[-80:],
        "ran_at": snapshot.get("ran_at"),
    }


# --- routes ------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/status")
def api_status():
    return status_payload()


@app.post("/api/config")
def api_config(body: ConfigBody):
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    updates = {}
    if body.api_key is not None:
        updates["GMGN_API_KEY"] = body.api_key
    if body.private_key is not None:
        updates["GMGN_PRIVATE_KEY"] = body.private_key
    if body.adapter is not None:
        if body.adapter.lower() not in ("mock", "cli"):
            return JSONResponse({"error": "adapter must be 'mock' or 'cli'"}, status_code=400)
        updates["GMGN_ADAPTER"] = body.adapter.lower()
    if body.buy_cmd is not None:
        updates["GMGN_BUY_CMD"] = body.buy_cmd
    if body.sell_cmd is not None:
        updates["GMGN_SELL_CMD"] = body.sell_cmd
    store.write_env(updates)
    with _state_lock:
        _adapters.clear()
        _trending_cache.clear()
    log_event("info", f"config updated ({', '.join(sorted(updates)) or 'no change'})")
    return status_payload()


@app.post("/api/mode")
def api_mode(body: ModeBody):
    global _mode
    mode = body.mode.upper()
    if mode not in ("SHADOW", "LIVE"):
        return JSONResponse({"error": "mode must be SHADOW or LIVE"}, status_code=400)
    if mode == "LIVE":
        if PUBLIC_DEMO:
            return JSONResponse({"error": "LIVE unavailable in PUBLIC_DEMO mode"}, status_code=403)
        if not body.confirm:
            return JSONResponse({"error": "LIVE mode requires confirm=true"}, status_code=400)
        if LIVE_TRADING_DISABLED:
            log_event("warn", "LIVE requested but LIVE_TRADING_DISABLED is True — orders stay simulated")
    _mode = mode
    log_event("warn" if mode == "LIVE" else "info", f"mode -> {mode}")
    return status_payload()


@app.get("/api/settings")
def api_get_settings(chain: str = "sol"):
    try:
        chain = validate_chain(chain)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return {
        "chain": chain,
        "command": store.get_trending_cmd(chain),
        "default": store.DEFAULT_TRENDING_CMD[chain],
    }


@app.post("/api/settings")
def api_set_settings(body: SettingsBody):
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    try:
        chain = validate_chain(body.chain)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if body.reset:
        command = store.reset_trending_cmd(chain)
    else:
        command = (body.command or "").strip()
        if not command.startswith("gmgn-cli market trending"):
            return JSONResponse(
                {"error": "command must start with 'gmgn-cli market trending'"}, status_code=400)
        store.set_trending_cmd(chain, command)
    with _state_lock:
        _trending_cache.pop(chain, None)
    log_event("info", f"{chain}: trending command updated")
    return {"chain": chain, "command": command, "default": store.DEFAULT_TRENDING_CMD[chain]}


class _CachedTrending:
    """Wraps an adapter so one round reuses a 3s-TTL trending result across tabs."""

    def __init__(self, adapter, chain):
        self._adapter = adapter
        self._chain = chain

    def __getattr__(self, name):
        return getattr(self._adapter, name)

    def trending(self, command, limit=100):
        now = time.time()
        with _state_lock:
            cached = _trending_cache.get(self._chain)
            if cached and cached[0] > now:
                return cached[1]
        rows = self._adapter.trending(command, limit=limit)
        with _state_lock:
            _trending_cache[self._chain] = (now + TRENDING_TTL_SECONDS, rows)
        return rows


@app.post("/api/run")
def api_run(body: RunBody):
    try:
        chain = validate_chain(body.chain)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    if PUBLIC_DEMO and chain in _last_round:
        return round_payload(chain)

    adapter = _CachedTrending(get_adapter(chain), chain)
    events = []
    try:
        candidates, rejected, funnel = screen(
            adapter, store.get_trending_cmd(chain), dev_cache=_dev_cache, events=events)
    except AdapterError as exc:
        log_event("error", f"{chain}: screening failed — {exc}")
        return JSONResponse({"error": str(exc)}, status_code=502)

    positions_mod.refresh(_positions, get_adapter, events=events)
    store.save_positions(_positions)

    for event in events:                       # after refresh, so escape alerts are included
        log_event(event["level"], f"{chain}: {event['text']}")

    with _state_lock:
        _last_round[chain] = {
            "candidates": candidates, "rejected": rejected,
            "funnel": funnel, "ran_at": time.time(),
        }

    store.log_decision("SCREEN", {
        "chain": chain, "funnel": funnel,
        "top": [{"symbol": c["symbol"], "address": c["address"],
                 "priority_score": c["priority_score"],
                 "dev_score": c.get("dev", {}).get("score"),
                 "llm": c.get("llm", {}).get("decision")} for c in candidates],
    })
    for candidate in rejected[:60]:
        store.log_decision("FILTER", {
            "chain": chain, "symbol": candidate.get("symbol"),
            "address": candidate.get("address"), "reason": candidate.get("reject_reason"),
            "gates": candidate.get("gates"),
        })
    return round_payload(chain)


def _find_candidate(chain, address):
    snapshot = _last_round.get(chain) or {}
    for candidate in snapshot.get("candidates", []):
        if candidate["address"] == address:
            return candidate
    return None


@app.get("/api/preflight")
def api_preflight(chain: str = "sol", address: str = "", side: str = "buy", amount: float = 0.05):
    """Show the exact argv a LIVE order would execute. Signs nothing."""
    try:
        chain = validate_chain(chain)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    adapter = get_adapter(chain)
    if not hasattr(adapter, "preflight_order"):
        return JSONResponse({"error": "current adapter places no real orders"}, status_code=400)
    argv = adapter.preflight_order(side, address or "<ADDRESS>",
                                   amount=amount, percent=100.0)
    return {"chain": chain, "side": side, "argv": argv,
            "would_execute": live_writes_allowed(adapter), "lock_reason": block_reason(adapter)}


@app.post("/api/buy")
def api_buy(body: BuyBody):
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    try:
        chain = validate_chain(body.chain)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    candidate = _find_candidate(chain, body.address)
    if candidate is None:
        return JSONResponse({"error": "token is not in the latest screening round"}, status_code=409)

    key = f"{chain}:{body.address}"
    if _positions.get(key, {}).get("status") == "open":
        return JSONResponse({"error": "position already open"}, status_code=409)

    allowed, reason, sizing = risk.check_buy(body.amount, _positions)
    if not allowed:
        store.log_decision("FILTER", {"chain": chain, "symbol": candidate["symbol"],
                                      "address": body.address, "reason": f"risk: {reason}"})
        log_event("warn", f"{candidate['symbol']}: buy blocked — {reason}")
        return JSONResponse({"error": reason, "sizing": sizing}, status_code=409)

    adapter = get_adapter(chain)
    permitted = live_writes_allowed(adapter)
    if permitted and not body.confirm:
        return JSONResponse({"error": "LIVE buy requires confirm=true", "sizing": sizing},
                            status_code=400)

    try:
        fill = adapter.place_order("buy", body.address, amount=sizing["size"],
                                   live_writes_allowed=permitted)
    except (AdapterError, LiveWriteBlocked) as exc:
        log_event("error", f"{candidate['symbol']}: buy failed — {exc}")
        return JSONResponse({"error": str(exc)}, status_code=502)

    if not fill.get("simulated") and fill.get("order_id"):
        fill = _poll_fill(adapter, fill)

    position = positions_mod.open_position(candidate, fill, sizing["size"], chain)
    _positions[position["key"]] = position
    store.save_positions(_positions)
    store.log_decision("BUY", {
        "chain": chain, "symbol": candidate["symbol"], "address": body.address,
        "size": sizing["size"], "sizing": sizing, "mode": _mode,
        "simulated": bool(fill.get("simulated")), "tx_hash": fill.get("tx_hash"),
        "order_id": fill.get("order_id"), "priority_score": candidate.get("priority_score"),
        "llm": candidate.get("llm"), "dev_score": candidate.get("dev", {}).get("score"),
    })
    log_event("info", f"{candidate['symbol']}: bought {sizing['size']} "
                      f"({'LIVE' if not fill.get('simulated') else 'paper'})")
    return {"position": position, "sizing": sizing, "fill": fill}


def _poll_fill(adapter, fill, attempts=10, delay=1.5):
    """Poll for a real fill and keep the transaction hash."""
    for _ in range(attempts):
        if fill.get("status") in ("filled", "failed", "cancelled"):
            break
        time.sleep(delay)
        try:
            update = adapter.order_status(fill["order_id"])
        except AdapterError:
            break
        fill.update({k: v for k, v in update.items() if v not in (None, "")})
    return fill


def _close(body, event_name):
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    position = _positions.get(body.key)
    if position is None or position.get("status") != "open":
        return JSONResponse({"error": "no open position for that key"}, status_code=404)

    adapter = get_adapter(position["chain"])
    permitted = live_writes_allowed(adapter) and not position.get("simulated")
    try:
        fill = adapter.place_order("sell", position["address"], percent=body.percent,
                                   live_writes_allowed=permitted)
    except (AdapterError, LiveWriteBlocked) as exc:
        log_event("error", f"{position['symbol']}: sell failed — {exc}")
        return JSONResponse({"error": str(exc)}, status_code=502)

    if not fill.get("simulated") and fill.get("order_id"):
        fill = _poll_fill(adapter, fill)

    positions_mod.close_position(position, fill)
    risk_state = risk.record_close(position.get("pnl", 0.0))
    store.save_positions(_positions)
    store.log_decision(event_name, {
        "chain": position["chain"], "symbol": position["symbol"],
        "address": position["address"], "pnl": position.get("pnl"),
        "pnl_pct": position.get("pnl_pct"), "mode": _mode,
        "simulated": bool(fill.get("simulated")), "tx_hash": fill.get("tx_hash"),
    })
    log_event("info", f"{position['symbol']}: closed at {position.get('pnl_pct', 0):+.2f}%")
    return {"position": position, "risk": risk_state}


@app.post("/api/sell")
def api_sell(body: PositionBody):
    return _close(body, "SELL")


@app.post("/api/unmonitor")
def api_unmonitor(body: PositionBody):
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    position = _positions.get(body.key)
    if position is None:
        return JSONResponse({"error": "no position for that key"}, status_code=404)
    position["monitored"] = False
    store.save_positions(_positions)
    store.log_decision("UNMONITOR", {"chain": position["chain"], "symbol": position["symbol"],
                                     "address": position["address"]})
    log_event("info", f"{position['symbol']}: monitoring stopped")
    return {"position": position}


@app.post("/api/risk/reset")
def api_risk_reset():
    if PUBLIC_DEMO:
        return JSONResponse({"error": "read-only in PUBLIC_DEMO mode"}, status_code=403)
    state = risk.reset_kill_switch()
    log_event("warn", "risk kill-switch reset")
    return {"risk": risk.summary(public_positions()), "state": state}


@app.get("/api/log")
def api_log(limit: int = 200):
    return {"events": _events[-80:], "decisions": store.tail_decisions(limit)}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    banner = "LIVE TRADING SEALED" if LIVE_TRADING_DISABLED else "LIVE TRADING ARMED"
    print(f"[gmgn-ai-trader] {banner} — http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
