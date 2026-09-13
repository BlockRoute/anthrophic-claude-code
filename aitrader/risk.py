"""Risk control and position sizing. Pure code — never an LLM decision.

Every limit here is a hard gate evaluated at trade time. State is persisted so a
tripped kill-switch survives a page reload or a backend restart.
"""

import time

import store

LIMITS = {
    # SPEC leaves this "relaxed to 20"; 3 is the production value and the safer
    # default for a wallet that can actually spend. Raise deliberately.
    "max_concurrent_positions": 3,
    "total_exposure_cap": 1.0,        # SOL-equivalent, notional at entry
    "daily_loss_cap": 0.5,           # SOL-equivalent realised loss per UTC day
    "consecutive_loss_limit": 3,     # kill-switch
    "max_single_buy": 0.25,          # SOL-equivalent per order
    "risk_fraction": 0.02,           # fixed-fraction sizing: equity at risk
    "stop_loss_distance": 0.35,      # assumed stop distance for sizing
    "default_equity": 1.0,
}


def _today():
    return time.strftime("%Y-%m-%d", time.gmtime())


def load_state():
    state = store.load_risk_state()
    day = _today()
    if state.get("day") != day:
        state = {"day": day, "realised_pnl": 0.0, "consecutive_losses": 0,
                 "kill_switch": False, "kill_reason": ""}
        store.save_risk_state(state)
    state.setdefault("realised_pnl", 0.0)
    state.setdefault("consecutive_losses", 0)
    state.setdefault("kill_switch", False)
    state.setdefault("kill_reason", "")
    return state


def record_close(realised_pnl, limits=None):
    """Fold a closed position's PnL into daily loss and consecutive-loss state."""
    cfg = {**LIMITS, **(limits or {})}
    state = load_state()
    state["realised_pnl"] = round(state["realised_pnl"] + realised_pnl, 6)
    if realised_pnl < 0:
        state["consecutive_losses"] += 1
    else:
        state["consecutive_losses"] = 0

    if state["consecutive_losses"] >= cfg["consecutive_loss_limit"]:
        state["kill_switch"] = True
        state["kill_reason"] = f"{state['consecutive_losses']} consecutive losses"
    if -state["realised_pnl"] >= cfg["daily_loss_cap"]:
        state["kill_switch"] = True
        state["kill_reason"] = f"daily loss cap {cfg['daily_loss_cap']} reached"

    store.save_risk_state(state)
    return state


def reset_kill_switch():
    state = load_state()
    state["kill_switch"] = False
    state["kill_reason"] = ""
    state["consecutive_losses"] = 0
    store.save_risk_state(state)
    return state


def exposure(positions):
    return round(sum(p.get("notional", 0.0) for p in positions.values() if p.get("status") == "open"), 6)


def position_size(requested_amount, positions, limits=None, equity=None):
    """Fixed-fraction sizing: risk_amount / stop_distance, then clipped by caps."""
    cfg = {**LIMITS, **(limits or {})}
    equity = cfg["default_equity"] if equity is None else equity
    model_size = (equity * cfg["risk_fraction"]) / max(cfg["stop_loss_distance"], 1e-6)
    headroom = max(0.0, cfg["total_exposure_cap"] - exposure(positions))
    size = min(requested_amount, model_size, cfg["max_single_buy"], headroom)
    return {
        "size": round(max(0.0, size), 6),
        "requested": requested_amount,
        "model_size": round(model_size, 6),
        "max_single_buy": cfg["max_single_buy"],
        "headroom": round(headroom, 6),
        "binding_constraint": min(
            (("requested", requested_amount), ("fixed_fraction", model_size),
             ("max_single_buy", cfg["max_single_buy"]), ("exposure_headroom", headroom)),
            key=lambda pair: pair[1],
        )[0],
    }


def check_buy(requested_amount, positions, limits=None, equity=None):
    """Hard pre-trade gate. Returns (allowed, reason, sizing)."""
    cfg = {**LIMITS, **(limits or {})}
    state = load_state()
    sizing = position_size(requested_amount, positions, cfg, equity)
    open_count = sum(1 for p in positions.values() if p.get("status") == "open")

    if state["kill_switch"]:
        return False, f"Kill-switch active: {state['kill_reason']}", sizing
    if open_count >= cfg["max_concurrent_positions"]:
        return False, f"Max concurrent positions ({cfg['max_concurrent_positions']}) reached", sizing
    if -state["realised_pnl"] >= cfg["daily_loss_cap"]:
        return False, f"Daily loss cap ({cfg['daily_loss_cap']}) reached", sizing
    if sizing["headroom"] <= 0:
        return False, f"Total exposure cap ({cfg['total_exposure_cap']}) reached", sizing
    if sizing["size"] <= 0:
        return False, "Computed position size is zero", sizing
    return True, "", sizing


def summary(positions, limits=None):
    cfg = {**LIMITS, **(limits or {})}
    state = load_state()
    open_count = sum(1 for p in positions.values() if p.get("status") == "open")
    return {
        "open_positions": open_count,
        "max_concurrent_positions": cfg["max_concurrent_positions"],
        "exposure": exposure(positions),
        "total_exposure_cap": cfg["total_exposure_cap"],
        "realised_pnl": state["realised_pnl"],
        "daily_loss_cap": cfg["daily_loss_cap"],
        "consecutive_losses": state["consecutive_losses"],
        "consecutive_loss_limit": cfg["consecutive_loss_limit"],
        "kill_switch": state["kill_switch"],
        "kill_reason": state["kill_reason"],
        "day": state["day"],
    }
