"""Screening pipeline: deterministic gates cast a wide net, scoring cuts hard,
the LLM only explains the survivors.

Stage order (SPEC):
    trending -> prefilter -> rug gate -> momentum ranking -> dev eval
    -> top 20 -> LLM explanation -> code-computed size

Only the security-scan budget deviates: a rug gate over all 100 prefiltered rows
would be 100 CLI calls per round, so rows are presorted by the momentum terms
that need no extra call, and the gate scans the best SECURITY_SCAN_LIMIT of them.
Everything below the budget is marked `skipped`, never `passed`.
"""

from adapters import AdapterError

GATES = ("prefilter", "rug_gate", "momentum", "dev_eval", "top20", "llm")

THRESHOLDS = {
    "prefilter_rows": 100,
    "min_liquidity": 4_000.0,
    "min_volume_5m": 750.0,
    "min_holders": 40,
    "max_age_minutes": 4_320.0,
    "security_scan_limit": 40,
    "max_buy_tax": 0.10,
    "max_sell_tax": 0.12,
    "max_bundler_ratio": 0.45,
    "max_top10_share": 0.80,
    "dev_eval_limit": 24,
    "min_dev_score": 0.15,
    "top_n": 20,
    "bleed_1h_pct": -12.0,
    "bleed_multiplier": 0.4,
}

WEIGHTS = {
    "momentum_5m": 30.0,
    "momentum_1h": 12.0,
    "buy_ratio": 18.0,
    "turnover": 12.0,
    "consensus": 12.0,
    "safe_float": 10.0,
    "dev_eval": 12.0,
}
WEIGHT_TOTAL = sum(WEIGHTS.values())


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _new_gates():
    return {gate: "pending" for gate in GATES}


# --- stage 1/2: trending + prefilter ----------------------------------------

def prefilter(rows, thresholds=None):
    """Trim trending output to tradeable rows. Returns (kept, rejected)."""
    cfg = {**THRESHOLDS, **(thresholds or {})}
    kept, rejected = [], []
    for row in rows[: cfg["prefilter_rows"]]:
        candidate = dict(row)
        candidate["gates"] = _new_gates()
        candidate["reject_reason"] = None
        reason = None
        if not candidate.get("address"):
            reason = "Missing token address"
        elif candidate.get("liquidity", 0) < cfg["min_liquidity"]:
            reason = f"Liquidity below ${cfg['min_liquidity']:,.0f}"
        elif candidate.get("volume_5m", 0) < cfg["min_volume_5m"]:
            reason = f"5m volume below ${cfg['min_volume_5m']:,.0f}"
        elif candidate.get("holders", 0) < cfg["min_holders"]:
            reason = f"Fewer than {cfg['min_holders']} holders"
        elif candidate.get("age_minutes", 0) > cfg["max_age_minutes"]:
            reason = "Older than the trending window"
        if reason:
            candidate["gates"]["prefilter"] = "failed"
            candidate["reject_reason"] = reason
            rejected.append(candidate)
        else:
            candidate["gates"]["prefilter"] = "passed"
            kept.append(candidate)
    return kept, rejected


# --- momentum terms ----------------------------------------------------------

def momentum_terms(candidate):
    """Normalised 0..1 scoring terms. Everything here is free of extra API calls
    except `dev_eval`, which stays 0 until the dev stage fills it in."""
    liquidity = max(1.0, candidate.get("liquidity", 0.0))
    buys = candidate.get("buy_count", 0)
    sells = candidate.get("sell_count", 0)
    holders = max(1, candidate.get("holders", 0))
    security = candidate.get("security") or {}

    buy_ratio = buys / (sells + 1.0)
    turnover = candidate.get("volume_5m", 0.0) / liquidity
    bundled = security.get("bundler_ratio", 0.0)
    breadth = clamp(buys / (holders * 0.5))
    top10 = security.get("top10_share", candidate.get("top10_share", 0.5))

    safe_float = clamp(1.0 - top10)
    if security:
        if security.get("lp_burned"):
            safe_float = clamp(safe_float + 0.1)
        if not security.get("renounced"):
            safe_float = clamp(safe_float - 0.15)

    return {
        "momentum_5m": clamp(candidate.get("momentum_5m", 0.0) / 60.0),
        "momentum_1h": clamp(candidate.get("momentum_1h", 0.0) / 120.0),
        "buy_ratio": clamp((buy_ratio - 0.8) / 2.2),
        "turnover": clamp(turnover / 1.5),
        "consensus": clamp(0.6 * breadth + 0.4 * (1.0 - clamp(bundled))),
        "safe_float": safe_float,
        "dev_eval": clamp(candidate.get("dev", {}).get("score", 0.0)),
    }


def priority_score(candidate, thresholds=None):
    """SPEC formula, rescaled to 0..100. Bleeding tokens take the sink multiplier."""
    cfg = {**THRESHOLDS, **(thresholds or {})}
    terms = momentum_terms(candidate)
    raw = sum(WEIGHTS[key] * terms[key] for key in WEIGHTS)
    score = raw / WEIGHT_TOTAL * 100.0
    sunk = candidate.get("momentum_1h", 0.0) < cfg["bleed_1h_pct"]
    if sunk:
        score *= cfg["bleed_multiplier"]
    candidate["score_terms"] = {key: round(value, 4) for key, value in terms.items()}
    candidate["score_sunk"] = sunk
    candidate["priority_score"] = round(score, 2)
    return candidate["priority_score"]


# --- stage 3: deterministic rug gate ----------------------------------------

def rug_gate(candidates, adapter, thresholds=None, events=None):
    """Hard security gate. Nothing advances on a judgement call."""
    cfg = {**THRESHOLDS, **(thresholds or {})}
    ordered = sorted(candidates, key=lambda c: priority_score(c, cfg), reverse=True)
    scanned, rejected, skipped = [], [], []

    for candidate in ordered[: cfg["security_scan_limit"]]:
        try:
            security = adapter.token_security(candidate["address"])
        except AdapterError as exc:
            candidate["gates"]["rug_gate"] = "failed"
            candidate["reject_reason"] = f"Security scan failed: {exc}"
            rejected.append(candidate)
            if events is not None:
                events.append({"level": "warn", "text": f"{candidate['symbol']}: security scan failed"})
            continue

        candidate["security"] = security
        reason = None
        if security.get("honeypot"):
            reason = "Honeypot"
        elif security.get("freezable"):
            reason = "Transfers freezable"
        elif security.get("buy_tax", 0) > cfg["max_buy_tax"]:
            reason = f"Buy tax {security['buy_tax'] * 100:.1f}%"
        elif security.get("sell_tax", 0) > cfg["max_sell_tax"]:
            reason = f"Sell tax {security['sell_tax'] * 100:.1f}%"
        elif security.get("bundler_ratio", 0) > cfg["max_bundler_ratio"]:
            reason = f"Bundled supply {security['bundler_ratio'] * 100:.0f}%"
        elif security.get("top10_share", 0) > cfg["max_top10_share"]:
            reason = f"Top-10 hold {security['top10_share'] * 100:.0f}%"
        elif security.get("mintable") and not security.get("renounced"):
            reason = "Mintable with live authority"

        if reason:
            candidate["gates"]["rug_gate"] = "failed"
            candidate["reject_reason"] = reason
            rejected.append(candidate)
        else:
            candidate["gates"]["rug_gate"] = "passed"
            scanned.append(candidate)

    for candidate in ordered[cfg["security_scan_limit"]:]:
        candidate["gates"]["rug_gate"] = "skipped"
        candidate["reject_reason"] = "Below security-scan budget"
        skipped.append(candidate)

    return scanned, rejected + skipped


# --- stage 5: developer reputation ------------------------------------------

def evaluate_dev(adapter, dev_address, recent_scan_limit=2):
    """Reputation 0..1 driven by per-token survival rate, minus unsafe patterns."""
    if not dev_address:
        return {"address": "", "score": 0.0, "penalties": ["Unknown creator"], "unknown": True}

    try:
        history = adapter.created_tokens(dev_address)
    except AdapterError as exc:
        return {"address": dev_address, "score": 0.0, "penalties": [f"History unavailable: {exc}"], "unknown": True}

    sampled = history.get("sampled", [])
    graduated = sum(1 for token in sampled if token.get("graduated"))
    stuck = sum(1 for token in sampled if token.get("stuck_in_curve"))
    denominator = graduated + stuck
    survival_rate = graduated / denominator if denominator else 0.0
    total = history.get("total_launches", denominator)
    stuck_backlog = int(round(total * (stuck / denominator))) if denominator else total

    penalties = []
    score = survival_rate

    if stuck_backlog >= 1_000:
        score -= 0.35
        penalties.append(f"{stuck_backlog} tokens stuck in curve (batch factory)")
    elif stuck_backlog >= 300:
        score -= 0.20
        penalties.append(f"{stuck_backlog} tokens stuck in curve")
    elif stuck_backlog >= 100:
        score -= 0.10
        penalties.append(f"{stuck_backlog} tokens stuck in curve")

    # Logo reuse counts only across the dev's OWN tokens: a creator whose art was
    # stolen by strangers is not penalised here.
    own_logos = [token.get("logo_hash") for token in sampled if token.get("logo_hash")]
    reskin = len(own_logos) >= 3 and len(set(own_logos)) <= max(1, len(own_logos) // 3)
    if reskin:
        score -= 0.15
        penalties.append("Reuses the same logo across own launches")

    recent = sorted(sampled, key=lambda token: token.get("created_at") or 0, reverse=True)[:recent_scan_limit]
    recent_unsafe = []
    for token in recent:
        if not token.get("address"):
            continue
        try:
            security = adapter.token_security(token["address"])
        except AdapterError:
            continue
        flags = [name for name in ("honeypot", "freezable") if security.get(name)]
        if security.get("mintable") and not security.get("renounced"):
            flags.append("mintable")   # mintable with a live authority; renounced is not a flag
        if flags:
            recent_unsafe.append({"symbol": token.get("symbol", "?"), "flags": flags})
    if recent_unsafe:
        score -= min(0.30, 0.15 * len(recent_unsafe))
        penalties.append(f"{len(recent_unsafe)} recent launch(es) unsafe")

    if history.get("exited"):
        score -= 0.20
        penalties.append("Creator wallet has exited prior positions")

    return {
        "address": dev_address,
        "launches": total,
        "sampled": denominator,
        "graduated": graduated,
        "stuck_in_curve": stuck,
        "stuck_backlog": stuck_backlog,
        "survival_rate": round(survival_rate, 4),
        "rug_rate": round(1.0 - survival_rate, 4),
        "alive": graduated,
        "reskin": reskin,
        "recent_unsafe": recent_unsafe,
        "exited": bool(history.get("exited")),
        "score": round(clamp(score), 4),
        "penalties": penalties,
        "unknown": False,
    }


def dev_gate(candidates, adapter, thresholds=None, dev_cache=None):
    cfg = {**THRESHOLDS, **(thresholds or {})}
    cache = dev_cache if dev_cache is not None else {}
    ordered = sorted(candidates, key=lambda c: c.get("priority_score", 0.0), reverse=True)
    passed, rejected = [], []

    for candidate in ordered[: cfg["dev_eval_limit"]]:
        dev_address = candidate.get("dev_address", "")
        if dev_address not in cache:
            cache[dev_address] = evaluate_dev(adapter, dev_address)
        candidate["dev"] = cache[dev_address]
        priority_score(candidate, cfg)          # rescore now that dev_eval is known
        if candidate["dev"]["score"] < cfg["min_dev_score"]:
            candidate["gates"]["dev_eval"] = "failed"
            candidate["reject_reason"] = "Low dev reputation"
            rejected.append(candidate)
        else:
            candidate["gates"]["dev_eval"] = "passed"
            passed.append(candidate)

    for candidate in ordered[cfg["dev_eval_limit"]:]:
        candidate["gates"]["dev_eval"] = "skipped"
        candidate["reject_reason"] = "Below dev-eval budget"
        rejected.append(candidate)

    return passed, rejected


# --- stage 7: LLM explanation (no gating authority) -------------------------

def heuristic_explain(candidate):
    """Placeholder standing in for the real judge. Explains, never gates, and
    never returns a position size."""
    terms = candidate.get("score_terms", {})
    score = candidate.get("priority_score", 0.0)
    dev = candidate.get("dev", {})
    notes = []

    if terms.get("momentum_5m", 0) > 0.6:
        notes.append("5m impulse is strong")
    elif terms.get("momentum_5m", 0) < 0.2:
        notes.append("5m impulse is thin")
    if terms.get("buy_ratio", 0) > 0.6:
        notes.append("buy pressure dominates prints")
    if terms.get("turnover", 0) > 0.6:
        notes.append("turnover is high against liquidity")
    if terms.get("consensus", 0) < 0.35:
        notes.append("participation looks narrow or bundled")
    if terms.get("safe_float", 0) < 0.35:
        notes.append("float is concentrated")
    if dev.get("survival_rate") is not None:
        notes.append(f"dev survival {dev.get('survival_rate', 0) * 100:.0f}%")
    if candidate.get("score_sunk"):
        notes.append("1h trend is bleeding, score sunk")

    if score >= 62 and not candidate.get("score_sunk"):
        decision, conviction = "BUY", clamp(0.55 + (score - 62) / 80)
    elif score >= 45:
        decision, conviction = "WATCH", clamp(0.3 + (score - 45) / 60)
    else:
        decision, conviction = "SKIP", clamp(score / 140)

    return {
        "decision": decision,
        "conviction": round(conviction, 3),
        "reasoning": "; ".join(notes) or "no distinguishing signal",
        "provider": "heuristic-placeholder",
    }


def explain(candidates, explainer=heuristic_explain):
    for candidate in candidates:
        candidate["llm"] = explainer(candidate)
        candidate["gates"]["llm"] = "passed"
    return candidates


# --- orchestration -----------------------------------------------------------

def screen(adapter, trending_command, thresholds=None, explainer=heuristic_explain,
           dev_cache=None, events=None):
    """Run one full round. Returns candidates, rejects, and funnel counts."""
    cfg = {**THRESHOLDS, **(thresholds or {})}
    log = events if events is not None else []

    rows = adapter.trending(trending_command, limit=cfg["prefilter_rows"])
    log.append({"level": "info", "text": f"trending returned {len(rows)} rows"})

    kept, rejected = prefilter(rows, cfg)
    log.append({"level": "info", "text": f"prefilter kept {len(kept)}/{len(rows)}"})

    safe, rug_rejects = rug_gate(kept, adapter, cfg, events=log)
    rejected += rug_rejects
    log.append({"level": "info", "text": f"rug gate cleared {len(safe)}"})

    for candidate in safe:
        priority_score(candidate, cfg)
        candidate["gates"]["momentum"] = "passed"

    dev_ok, dev_rejects = dev_gate(safe, adapter, cfg, dev_cache=dev_cache)
    rejected += dev_rejects
    log.append({"level": "info", "text": f"dev gate cleared {len(dev_ok)}"})

    dev_ok.sort(key=lambda c: c.get("priority_score", 0.0), reverse=True)
    finalists = dev_ok[: cfg["top_n"]]
    for candidate in finalists:
        candidate["gates"]["top20"] = "passed"
    for candidate in dev_ok[cfg["top_n"]:]:
        candidate["gates"]["top20"] = "failed"
        candidate["reject_reason"] = f"Outside top {cfg['top_n']}"
        rejected.append(candidate)

    explain(finalists, explainer)
    log.append({"level": "info", "text": f"LLM explained {len(finalists)} survivors"})

    for rank, candidate in enumerate(finalists, start=1):
        candidate["rank"] = rank

    funnel = {
        "trending": len(rows),
        "prefilter": len(kept),
        "rug_gate": len(safe),
        "dev_eval": len(dev_ok),
        "top20": len(finalists),
        "llm": len(finalists),
    }
    return finalists, rejected, funnel
