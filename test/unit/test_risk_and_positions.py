import pytest

import positions as positions_mod
import risk


def make_position(notional=0.1, status="open", **overrides):
    position = {"key": f"sol:{id(overrides)}", "status": status, "notional": notional,
                "monitored": True,
                "size": notional, "chain": "sol", "address": "a", "symbol": "T",
                "entry_price": 1.0, "current_price": 1.0,
                "entry_snapshot": {"honeypot": False, "mintable": False, "renounced": True,
                                   "freezable": False, "sell_tax": 0.0, "top10_share": 0.2},
                "escape": {"severity": 0, "signals": [], "pulse": False}}
    position.update(overrides)
    return position


# --- sizing ------------------------------------------------------------------

def test_position_size_uses_fixed_fraction_model():
    sizing = risk.position_size(10.0, {})
    expected = risk.LIMITS["default_equity"] * risk.LIMITS["risk_fraction"] / risk.LIMITS["stop_loss_distance"]
    assert sizing["size"] == pytest.approx(expected, abs=1e-6)
    assert sizing["binding_constraint"] == "fixed_fraction"


def test_requested_amount_can_bind_below_the_model():
    sizing = risk.position_size(0.01, {})
    assert sizing["size"] == pytest.approx(0.01)
    assert sizing["binding_constraint"] == "requested"


def test_exposure_headroom_clips_the_size():
    positions = {"a": make_position(notional=0.98)}
    sizing = risk.position_size(1.0, positions)
    assert sizing["size"] == pytest.approx(0.02, abs=1e-6)
    assert sizing["binding_constraint"] == "exposure_headroom"


def test_closed_positions_do_not_count_toward_exposure():
    positions = {"a": make_position(notional=0.5, status="closed")}
    assert risk.exposure(positions) == 0.0


# --- pre-trade gate ----------------------------------------------------------

def test_buy_allowed_when_flat():
    allowed, reason, _ = risk.check_buy(0.05, {})
    assert allowed and reason == ""


def test_max_concurrent_positions_blocks():
    positions = {str(i): make_position(notional=0.01) for i in range(risk.LIMITS["max_concurrent_positions"])}
    allowed, reason, _ = risk.check_buy(0.05, positions)
    assert not allowed and "Max concurrent positions" in reason


def test_total_exposure_cap_blocks():
    positions = {"a": make_position(notional=risk.LIMITS["total_exposure_cap"])}
    allowed, reason, _ = risk.check_buy(0.05, positions)
    assert not allowed and "Total exposure cap" in reason


def test_consecutive_losses_trip_the_kill_switch():
    for _ in range(risk.LIMITS["consecutive_loss_limit"]):
        state = risk.record_close(-0.01)
    assert state["kill_switch"] is True
    allowed, reason, _ = risk.check_buy(0.05, {})
    assert not allowed and "Kill-switch" in reason


def test_a_win_resets_the_consecutive_loss_counter():
    risk.record_close(-0.01)
    risk.record_close(-0.01)
    state = risk.record_close(0.05)
    assert state["consecutive_losses"] == 0 and state["kill_switch"] is False


def test_daily_loss_cap_trips_the_kill_switch():
    state = risk.record_close(-risk.LIMITS["daily_loss_cap"])
    assert state["kill_switch"] is True
    assert "daily loss cap" in state["kill_reason"]


def test_kill_switch_state_survives_a_restart():
    risk.record_close(-risk.LIMITS["daily_loss_cap"])
    assert risk.load_state()["kill_switch"] is True   # re-read from disk, not memory
    assert risk.reset_kill_switch()["kill_switch"] is False
    assert risk.load_state()["kill_switch"] is False


# --- escape monitor ----------------------------------------------------------

def security(**overrides):
    base = {"honeypot": False, "mintable": False, "renounced": True, "freezable": False,
            "sell_tax": 0.0, "top10_share": 0.2}
    base.update(overrides)
    return base


def test_clean_position_has_zero_severity():
    severity, signals = positions_mod.escape_signals(make_position(), security())
    assert severity == 0 and signals == []


def test_honeypot_after_entry_is_the_heaviest_signal():
    severity, signals = positions_mod.escape_signals(make_position(), security(honeypot=True))
    assert severity == positions_mod.ESCAPE_WEIGHTS["honeypot"]
    assert signals[0]["code"] == "honeypot"


def test_honeypot_present_at_entry_is_not_a_new_signal():
    position = make_position()
    position["entry_snapshot"]["honeypot"] = True
    severity, signals = positions_mod.escape_signals(position, security(honeypot=True))
    assert severity == 0 and signals == []


def test_revoked_renounce_and_returned_mint_both_fire():
    severity, signals = positions_mod.escape_signals(
        make_position(), security(renounced=False, mintable=True))
    codes = {s["code"] for s in signals}
    assert codes == {"renounce_revoked", "mint_authority_returned"}
    assert severity == 60


def test_concentration_spike_scales_with_the_move():
    small = positions_mod.escape_signals(make_position(), security(top10_share=0.31))[0]
    large = positions_mod.escape_signals(make_position(), security(top10_share=0.80))[0]
    assert 0 < small <= large <= positions_mod.ESCAPE_WEIGHTS["concentration_spike"]


def test_concentration_below_the_threshold_is_ignored():
    severity, _ = positions_mod.escape_signals(make_position(), security(top10_share=0.25))
    assert severity == 0


def test_sell_tax_spike_fires():
    severity, signals = positions_mod.escape_signals(make_position(), security(sell_tax=0.2))
    assert signals[0]["code"] == "sell_tax_spike"
    assert severity == positions_mod.ESCAPE_WEIGHTS["sell_tax_spike"]


def test_severity_is_clamped_to_100_and_pulses():
    severity, _ = positions_mod.escape_signals(
        make_position(), security(honeypot=True, mintable=True, renounced=False,
                                  freezable=True, top10_share=0.9, sell_tax=0.3))
    assert severity == 100 >= positions_mod.PULSE_THRESHOLD


def test_refresh_reprices_and_flags(monkeypatch):
    class DegradingAdapter:
        def token_price(self, address):
            return {"price": 2.0, "liquidity": 1_000.0}

        def token_security(self, address, **_):
            return security(honeypot=True, top10_share=0.9)

    positions = {"k": make_position()}
    events = []
    positions_mod.refresh(positions, lambda chain: DegradingAdapter(), events=events)
    position = positions["k"]
    assert position["pnl_pct"] == pytest.approx(100.0)
    assert position["escape"]["pulse"] is True
    assert any("exit now" in event["text"] for event in events)


def test_refresh_skips_unmonitored_positions():
    class Boom:
        def token_price(self, address):
            raise AssertionError("should not be polled")

        token_security = token_price

    positions = {"k": make_position(monitored=False)}
    positions_mod.refresh(positions, lambda chain: Boom())


def test_close_position_computes_realised_pnl():
    position = make_position(size=0.1, entry_price=1.0)
    positions_mod.close_position(position, {"fill_price": 1.5, "simulated": True})
    assert position["status"] == "closed"
    assert position["pnl_pct"] == pytest.approx(50.0)
    assert position["pnl"] == pytest.approx(0.05)
    assert position["notional"] == 0.0
