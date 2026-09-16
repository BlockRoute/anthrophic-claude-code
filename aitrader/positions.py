"""Position state and the escape monitor.

The escape monitor is deliberately separate from screening: it compares a
position against the entry snapshot taken at buy time and never re-runs any
screening logic. Severity is a pure function of observed degradation.
"""

import time

from adapters import AdapterError

ESCAPE_WEIGHTS = {
    "honeypot": 50,
    "mint_authority_returned": 30,
    "renounce_revoked": 30,
    "freezable": 25,
    "concentration_spike": 30,
    "sell_tax_spike": 20,
}
PULSE_THRESHOLD = 70
CONCENTRATION_SPIKE = 0.10          # absolute top-10 share increase
SELL_TAX_SPIKE = 0.05


def entry_snapshot(candidate):
    security = candidate.get("security") or {}
    return {
        "price": candidate.get("price", 0.0),
        "liquidity": candidate.get("liquidity", 0.0),
        "honeypot": bool(security.get("honeypot")),
        "mintable": bool(security.get("mintable")),
        "renounced": bool(security.get("renounced")),
        "freezable": bool(security.get("freezable")),
        "sell_tax": security.get("sell_tax", 0.0),
        "top10_share": security.get("top10_share", candidate.get("top10_share", 0.0)),
    }


def open_position(candidate, fill, size, chain):
    entry_price = fill.get("fill_price") or candidate.get("price") or 0.0
    return {
        "key": f"{chain}:{candidate['address']}",
        "chain": chain,
        "address": candidate["address"],
        "symbol": candidate.get("symbol", "?"),
        "status": "open",
        "monitored": True,
        "opened_at": time.time(),
        "entry_price": entry_price,
        "current_price": entry_price,
        "size": size,
        "notional": round(size, 6),
        "pnl_pct": 0.0,
        "pnl": 0.0,
        "order": fill,
        "entry_snapshot": entry_snapshot(candidate),
        "escape": {"severity": 0, "signals": [], "pulse": False, "checked_at": time.time()},
        "simulated": bool(fill.get("simulated")),
    }


def escape_signals(position, security, price_info=None):
    """Compare live security against the entry snapshot. Returns (severity, signals)."""
    snapshot = position.get("entry_snapshot", {})
    signals = []

    if security.get("honeypot") and not snapshot.get("honeypot"):
        signals.append({"code": "honeypot", "text": "Honeypot triggered after entry",
                        "weight": ESCAPE_WEIGHTS["honeypot"]})
    if security.get("mintable") and not snapshot.get("mintable"):
        signals.append({"code": "mint_authority_returned", "text": "Mint authority reappeared",
                        "weight": ESCAPE_WEIGHTS["mint_authority_returned"]})
    if snapshot.get("renounced") and not security.get("renounced"):
        signals.append({"code": "renounce_revoked", "text": "Ownership renounce revoked",
                        "weight": ESCAPE_WEIGHTS["renounce_revoked"]})
    if security.get("freezable") and not snapshot.get("freezable"):
        signals.append({"code": "freezable", "text": "Transfers became freezable",
                        "weight": ESCAPE_WEIGHTS["freezable"]})

    entry_top10 = snapshot.get("top10_share", 0.0)
    live_top10 = security.get("top10_share", entry_top10)
    if live_top10 - entry_top10 >= CONCENTRATION_SPIKE:
        scaled = min(ESCAPE_WEIGHTS["concentration_spike"],
                     int(ESCAPE_WEIGHTS["concentration_spike"] * (live_top10 - entry_top10) / 0.3))
        signals.append({"code": "concentration_spike",
                        "text": f"Top-10 share {entry_top10 * 100:.0f}% -> {live_top10 * 100:.0f}%",
                        "weight": max(10, scaled)})

    entry_tax = snapshot.get("sell_tax", 0.0)
    live_tax = security.get("sell_tax", entry_tax)
    if live_tax - entry_tax >= SELL_TAX_SPIKE:
        signals.append({"code": "sell_tax_spike",
                        "text": f"Sell tax {entry_tax * 100:.1f}% -> {live_tax * 100:.1f}%",
                        "weight": ESCAPE_WEIGHTS["sell_tax_spike"]})

    severity = min(100, sum(signal["weight"] for signal in signals))
    return severity, signals


def refresh(positions, adapter_for_chain, events=None):
    """Re-price and re-scan every monitored position."""
    for position in positions.values():
        if position.get("status") != "open" or not position.get("monitored"):
            continue
        try:
            adapter = adapter_for_chain(position["chain"])
            price_info = adapter.token_price(position["address"])
            security = adapter.token_security(position["address"])
        except AdapterError as exc:
            position["escape"]["error"] = str(exc)
            continue

        position["escape"].pop("error", None)
        price = price_info.get("price") or position["current_price"]
        position["current_price"] = price
        entry = position.get("entry_price") or 0.0
        if entry:
            position["pnl_pct"] = round((price - entry) / entry * 100.0, 2)
            position["pnl"] = round(position["size"] * (price - entry) / entry, 6)

        severity, signals = escape_signals(position, security, price_info)
        was_pulsing = position["escape"].get("pulse")
        position["escape"] = {
            "severity": severity,
            "signals": signals,
            "pulse": severity >= PULSE_THRESHOLD,
            "checked_at": time.time(),
        }
        if events is not None and position["escape"]["pulse"] and not was_pulsing:
            events.append({"level": "alert",
                           "text": f"{position['symbol']}: ESCAPE severity {severity} — exit now"})
    return positions


def close_position(position, fill):
    position["status"] = "closed"
    position["monitored"] = False
    position["closed_at"] = time.time()
    position["close_order"] = fill
    exit_price = fill.get("fill_price") or position.get("current_price") or position.get("entry_price")
    entry = position.get("entry_price") or 0.0
    if entry:
        position["pnl_pct"] = round((exit_price - entry) / entry * 100.0, 2)
        position["pnl"] = round(position["size"] * (exit_price - entry) / entry, 6)
    position["notional"] = 0.0
    return position
