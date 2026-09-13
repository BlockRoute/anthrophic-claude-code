import pytest

import pipeline
from adapters import MockGMGN


def make_row(**overrides):
    row = {
        "symbol": "TEST", "name": "Test", "address": "addr-1", "chain": "sol",
        "price": 0.001, "liquidity": 50_000.0, "market_cap": 500_000.0,
        "volume_5m": 25_000.0, "volume_1h": 200_000.0,
        "momentum_5m": 40.0, "momentum_1h": 60.0,
        "buy_count": 400, "sell_count": 100, "holders": 900,
        "top10_share": 0.3, "age_minutes": 120, "dev_address": "dev-1",
    }
    row.update(overrides)
    return row


class StubAdapter:
    def __init__(self, security=None, history=None):
        self._security = security or {}
        self._history = history or {"total_launches": 0, "sampled": [], "exited": False}

    def token_security(self, address, **_):
        base = {"honeypot": False, "mintable": False, "renounced": True, "freezable": False,
                "buy_tax": 0.0, "sell_tax": 0.0, "lp_burned": True,
                "bundler_ratio": 0.1, "top10_share": 0.3, "logo_hash": "x"}
        base.update(self._security)
        base["address"] = address
        return base

    def created_tokens(self, dev_address, limit=50):
        return dict(self._history, dev_address=dev_address)


# --- prefilter ---------------------------------------------------------------

@pytest.mark.parametrize("overrides,expected", [
    ({}, None),
    ({"liquidity": 100.0}, "Liquidity below $4,000"),
    ({"volume_5m": 10.0}, "5m volume below $750"),
    ({"holders": 3}, "Fewer than 40 holders"),
    ({"age_minutes": 99_999}, "Older than the trending window"),
    ({"address": ""}, "Missing token address"),
])
def test_prefilter_reasons(overrides, expected):
    kept, rejected = pipeline.prefilter([make_row(**overrides)])
    if expected is None:
        assert len(kept) == 1 and kept[0]["gates"]["prefilter"] == "passed"
    else:
        assert kept == []
        assert rejected[0]["reject_reason"] == expected
        assert rejected[0]["gates"]["prefilter"] == "failed"


def test_prefilter_caps_at_configured_row_count():
    rows = [make_row(address=f"a{i}") for i in range(150)]
    kept, rejected = pipeline.prefilter(rows)
    assert len(kept) + len(rejected) == pipeline.THRESHOLDS["prefilter_rows"]


# --- rug gate ----------------------------------------------------------------

@pytest.mark.parametrize("security,expected", [
    ({}, None),
    ({"honeypot": True}, "Honeypot"),
    ({"freezable": True}, "Transfers freezable"),
    ({"buy_tax": 0.2}, "Buy tax 20.0%"),
    ({"sell_tax": 0.3}, "Sell tax 30.0%"),
    ({"bundler_ratio": 0.9}, "Bundled supply 90%"),
    ({"top10_share": 0.95}, "Top-10 hold 95%"),
    ({"mintable": True, "renounced": False}, "Mintable with live authority"),
])
def test_rug_gate_is_deterministic(security, expected):
    kept, _ = pipeline.prefilter([make_row()])
    safe, rejected = pipeline.rug_gate(kept, StubAdapter(security))
    if expected is None:
        assert len(safe) == 1 and safe[0]["gates"]["rug_gate"] == "passed"
    else:
        assert safe == []
        assert rejected[0]["reject_reason"] == expected


def test_rug_gate_allows_mintable_when_renounced():
    kept, _ = pipeline.prefilter([make_row()])
    safe, _ = pipeline.rug_gate(kept, StubAdapter({"mintable": True, "renounced": True}))
    assert len(safe) == 1


def test_rug_gate_marks_overflow_skipped_not_passed():
    rows = [make_row(address=f"a{i}") for i in range(60)]
    kept, _ = pipeline.prefilter(rows)
    safe, rejected = pipeline.rug_gate(kept, StubAdapter())
    assert len(safe) == pipeline.THRESHOLDS["security_scan_limit"]
    skipped = [c for c in rejected if c["gates"]["rug_gate"] == "skipped"]
    assert len(skipped) == len(kept) - pipeline.THRESHOLDS["security_scan_limit"]
    assert all(c["reject_reason"] == "Below security-scan budget" for c in skipped)


# --- scoring -----------------------------------------------------------------

def test_priority_score_matches_weighted_formula():
    candidate = make_row()
    candidate["gates"] = {}
    candidate["dev"] = {"score": 0.5}
    score = pipeline.priority_score(candidate)
    terms = candidate["score_terms"]
    expected = sum(pipeline.WEIGHTS[k] * terms[k] for k in pipeline.WEIGHTS)
    assert score == pytest.approx(expected / pipeline.WEIGHT_TOTAL * 100, abs=0.02)


def test_bleeding_token_takes_the_sink_multiplier():
    healthy = make_row(momentum_1h=5.0)
    healthy["dev"] = {"score": 0.5}
    bleeding = make_row(momentum_1h=-20.0)
    bleeding["dev"] = {"score": 0.5}
    pipeline.priority_score(healthy)
    pipeline.priority_score(bleeding)
    assert bleeding["score_sunk"] is True
    assert healthy["score_sunk"] is False
    # same terms except the 1h component; the sink dominates
    assert bleeding["priority_score"] < healthy["priority_score"] * 0.5


def test_score_terms_stay_normalised():
    candidate = make_row(momentum_5m=9_999, buy_count=99_999, volume_5m=1e9)
    candidate["dev"] = {"score": 1.0}
    pipeline.priority_score(candidate)
    assert all(0.0 <= v <= 1.0 for v in candidate["score_terms"].values())
    assert candidate["priority_score"] <= 100.0


# --- developer reputation ----------------------------------------------------

def history(graduated, stuck, total=None, exited=False, logo=None):
    sampled = [{"address": f"g{i}", "symbol": f"G{i}", "graduated": True,
                "stuck_in_curve": False, "logo_hash": logo or f"lg{i}", "created_at": i}
               for i in range(graduated)]
    sampled += [{"address": f"s{i}", "symbol": f"S{i}", "graduated": False,
                 "stuck_in_curve": True, "logo_hash": logo or f"ls{i}", "created_at": i}
                for i in range(stuck)]
    return {"total_launches": total if total is not None else graduated + stuck,
            "sampled": sampled, "exited": exited}


def test_dev_score_is_survival_rate_when_clean():
    adapter = StubAdapter(history=history(3, 1))
    result = pipeline.evaluate_dev(adapter, "dev-1", recent_scan_limit=0)
    assert result["survival_rate"] == pytest.approx(0.75)
    assert result["score"] == pytest.approx(0.75)
    assert result["penalties"] == []


def test_token_factory_is_crushed_by_backlog_penalty():
    adapter = StubAdapter(history=history(1, 99, total=2_000))
    result = pipeline.evaluate_dev(adapter, "factory", recent_scan_limit=0)
    assert result["survival_rate"] == pytest.approx(0.01)
    assert result["score"] == 0.0
    assert any("batch factory" in p for p in result["penalties"])


def test_self_logo_reuse_is_penalised():
    adapter = StubAdapter(history=history(6, 0, logo="same"))
    result = pipeline.evaluate_dev(adapter, "reskinner", recent_scan_limit=0)
    assert result["reskin"] is True
    assert result["score"] == pytest.approx(0.85)


def test_exited_wallet_is_penalised():
    adapter = StubAdapter(history=history(4, 0, exited=True))
    result = pipeline.evaluate_dev(adapter, "exited", recent_scan_limit=0)
    assert result["score"] == pytest.approx(0.80)


def test_recent_unsafe_launch_penalty_ignores_renounced_mintable():
    safe_mintable = StubAdapter(security={"mintable": True, "renounced": True},
                                history=history(4, 0))
    live_authority = StubAdapter(security={"mintable": True, "renounced": False},
                                 history=history(4, 0))
    assert pipeline.evaluate_dev(safe_mintable, "d", recent_scan_limit=2)["score"] == pytest.approx(1.0)
    assert pipeline.evaluate_dev(live_authority, "d", recent_scan_limit=2)["score"] < 1.0


def test_unknown_creator_scores_zero():
    result = pipeline.evaluate_dev(StubAdapter(), "")
    assert result["score"] == 0.0 and result["unknown"] is True


def test_dev_gate_rejects_below_threshold():
    kept, _ = pipeline.prefilter([make_row()])
    safe, _ = pipeline.rug_gate(kept, StubAdapter())
    adapter = StubAdapter(history=history(0, 20))
    passed, rejected = pipeline.dev_gate(safe, adapter)
    assert passed == []
    assert rejected[0]["reject_reason"] == "Low dev reputation"
    assert rejected[0]["gates"]["dev_eval"] == "failed"


def test_dev_cache_avoids_repeat_lookups():
    calls = []

    class CountingAdapter(StubAdapter):
        def created_tokens(self, dev_address, limit=50):
            calls.append(dev_address)
            return super().created_tokens(dev_address, limit)

    rows = [make_row(address=f"a{i}", dev_address="shared") for i in range(5)]
    kept, _ = pipeline.prefilter(rows)
    adapter = CountingAdapter(history=history(4, 0))
    safe, _ = pipeline.rug_gate(kept, adapter)
    pipeline.dev_gate(safe, adapter, dev_cache={})
    assert calls == ["shared"]


# --- judge -------------------------------------------------------------------

def test_judge_never_gates_and_never_sizes():
    candidate = make_row()
    candidate["gates"] = {}
    candidate["dev"] = {"score": 0.9, "survival_rate": 0.9}
    pipeline.priority_score(candidate)
    verdict = pipeline.heuristic_explain(candidate)
    assert verdict["decision"] in ("BUY", "WATCH", "SKIP")
    assert 0.0 <= verdict["conviction"] <= 1.0
    assert "size" not in verdict and "amount" not in verdict


def test_explain_marks_every_survivor_passed():
    candidates = []
    for index in range(3):
        candidate = make_row(address=f"a{index}")
        candidate["gates"] = {"llm": "pending"}
        candidate["dev"] = {"score": 0.5}
        pipeline.priority_score(candidate)
        candidates.append(candidate)
    pipeline.explain(candidates)
    assert all(c["gates"]["llm"] == "passed" for c in candidates)


# --- full round --------------------------------------------------------------

def test_screen_round_is_internally_consistent():
    adapter = MockGMGN(chain="sol", seed=44)
    finalists, rejected, funnel = pipeline.screen(
        adapter, "gmgn-cli market trending --chain sol")
    assert funnel["trending"] >= funnel["prefilter"] >= funnel["rug_gate"]
    assert funnel["rug_gate"] >= funnel["dev_eval"] >= funnel["top20"]
    assert funnel["top20"] == len(finalists) <= pipeline.THRESHOLDS["top_n"]
    assert [c["rank"] for c in finalists] == list(range(1, len(finalists) + 1))
    scores = [c["priority_score"] for c in finalists]
    assert scores == sorted(scores, reverse=True)
    assert all(c["llm"]["decision"] for c in finalists)
    assert all(c["reject_reason"] for c in rejected)
