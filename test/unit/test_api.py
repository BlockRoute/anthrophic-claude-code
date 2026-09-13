import pytest
from fastapi.testclient import TestClient

import app as app_module
import store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "_mode", "SHADOW")
    monkeypatch.setattr(app_module, "LIVE_TRADING_DISABLED", True)
    app_module._positions.clear()
    app_module._last_round.clear()
    app_module._adapters.clear()
    app_module._trending_cache.clear()
    app_module._dev_cache.clear()
    del app_module._events[:]
    return TestClient(app_module.app)


def run_round(client, chain="sol"):
    response = client.post("/api/run", json={"chain": chain})
    assert response.status_code == 200
    return response.json()


# --- status ------------------------------------------------------------------

def test_status_reports_the_lock(client):
    status = client.get("/api/status").json()
    assert status["mode"] == "SHADOW"
    assert status["trading_locked"] is True
    assert status["live_trading_disabled"] is True


def test_status_never_leaks_key_material(client):
    store.write_env({"GMGN_API_KEY": "secret-key", "GMGN_PRIVATE_KEY": "secret-signer"})
    body = client.get("/api/status").text
    assert "secret-key" not in body and "secret-signer" not in body
    assert client.get("/api/status").json()["signing_key_present"] is True


def test_env_file_is_written_chmod_600(client):
    client.post("/api/config", json={"api_key": "abc"})
    assert oct(store.ENV_PATH.stat().st_mode)[-3:] == "600"


# --- chains ------------------------------------------------------------------

def test_unknown_chain_is_rejected(client):
    assert client.post("/api/run", json={"chain": "doge"}).status_code == 400
    assert client.get("/api/settings", params={"chain": "doge"}).status_code == 400


@pytest.mark.parametrize("chain", ["sol", "bsc", "base", "eth"])
def test_every_chain_screens_independently(client, chain):
    payload = run_round(client, chain)
    assert payload["chain"] == chain
    assert all(c["chain"] == chain for c in payload["candidates"])


# --- settings ----------------------------------------------------------------

def test_trending_command_prefix_is_enforced(client):
    response = client.post("/api/settings", json={"chain": "sol", "command": "curl evil.example"})
    assert response.status_code == 400
    assert "gmgn-cli market trending" in response.json()["error"]


def test_custom_command_persists_and_resets(client):
    custom = "gmgn-cli market trending --chain sol --timeframe 1h"
    client.post("/api/settings", json={"chain": "sol", "command": custom})
    assert client.get("/api/settings", params={"chain": "sol"}).json()["command"] == custom
    client.post("/api/settings", json={"chain": "sol", "reset": True})
    assert client.get("/api/settings", params={"chain": "sol"}).json()["command"] == \
        store.DEFAULT_TRENDING_CMD["sol"]


def test_settings_are_per_chain(client):
    client.post("/api/settings", json={"chain": "bsc", "command": "gmgn-cli market trending --chain bsc"})
    assert client.get("/api/settings", params={"chain": "sol"}).json()["command"] == \
        store.DEFAULT_TRENDING_CMD["sol"]


# --- mode --------------------------------------------------------------------

def test_live_requires_explicit_confirmation(client):
    assert client.post("/api/mode", json={"mode": "LIVE"}).status_code == 400
    assert client.post("/api/mode", json={"mode": "LIVE", "confirm": True}).status_code == 200


def test_live_mode_still_locked_by_the_master_switch(client):
    status = client.post("/api/mode", json={"mode": "LIVE", "confirm": True}).json()
    assert status["mode"] == "LIVE"
    assert status["trading_locked"] is True
    assert "LIVE_TRADING_DISABLED" in status["lock_reason"]


def test_invalid_mode_rejected(client):
    assert client.post("/api/mode", json={"mode": "YOLO", "confirm": True}).status_code == 400


def test_mock_adapter_cannot_write_even_with_the_switch_off(client, monkeypatch):
    monkeypatch.setattr(app_module, "LIVE_TRADING_DISABLED", False)
    client.post("/api/mode", json={"mode": "LIVE", "confirm": True})
    status = client.get("/api/status").json()
    assert status["trading_locked"] is True
    assert "MockGMGN" in status["lock_reason"]


# --- trading -----------------------------------------------------------------

def test_buy_rejects_a_token_outside_the_last_round(client):
    run_round(client)
    response = client.post("/api/buy", json={"chain": "sol", "address": "not-screened", "amount": 0.05})
    assert response.status_code == 409


def test_buy_opens_a_simulated_position_and_logs_it(client):
    payload = run_round(client)
    candidate = payload["candidates"][0]
    result = client.post("/api/buy", json={"chain": "sol", "address": candidate["address"],
                                           "amount": 0.05}).json()
    position = result["position"]
    assert position["simulated"] is True and position["status"] == "open"
    assert position["entry_snapshot"]["top10_share"] is not None
    events = [d["event"] for d in client.get("/api/log").json()["decisions"]]
    assert "BUY" in events and "SCREEN" in events


def test_buying_the_same_token_twice_is_rejected(client):
    candidate = run_round(client)["candidates"][0]
    body = {"chain": "sol", "address": candidate["address"], "amount": 0.05}
    assert client.post("/api/buy", json=body).status_code == 200
    assert client.post("/api/buy", json=body).status_code == 409


def test_buy_is_blocked_once_the_kill_switch_trips(client):
    import risk

    candidate = run_round(client)["candidates"][0]
    for _ in range(risk.LIMITS["consecutive_loss_limit"]):
        risk.record_close(-0.01)
    response = client.post("/api/buy", json={"chain": "sol", "address": candidate["address"],
                                             "amount": 0.05})
    assert response.status_code == 409
    assert "Kill-switch" in response.json()["error"]
    assert client.post("/api/risk/reset").json()["risk"]["kill_switch"] is False


def test_sell_closes_the_position_and_records_pnl(client):
    candidate = run_round(client)["candidates"][0]
    key = client.post("/api/buy", json={"chain": "sol", "address": candidate["address"],
                                        "amount": 0.05}).json()["position"]["key"]
    result = client.post("/api/sell", json={"key": key}).json()
    assert result["position"]["status"] == "closed"
    assert "pnl" in result["position"]
    assert client.post("/api/run", json={"chain": "sol"}).json()["risk"]["exposure"] == 0.0


def test_sell_on_an_unknown_key_is_404(client):
    assert client.post("/api/sell", json={"key": "sol:nope"}).status_code == 404


def test_unmonitor_keeps_the_position_but_stops_polling(client):
    candidate = run_round(client)["candidates"][0]
    key = client.post("/api/buy", json={"chain": "sol", "address": candidate["address"],
                                        "amount": 0.05}).json()["position"]["key"]
    position = client.post("/api/unmonitor", json={"key": key}).json()["position"]
    assert position["monitored"] is False and position["status"] == "open"


def test_positions_survive_a_backend_restart(client):
    candidate = run_round(client)["candidates"][0]
    client.post("/api/buy", json={"chain": "sol", "address": candidate["address"], "amount": 0.05})
    assert len(store.load_positions()) == 1


# --- preflight ---------------------------------------------------------------

def test_preflight_is_unavailable_on_the_mock_adapter(client):
    assert client.get("/api/preflight", params={"chain": "sol", "address": "TOK"}).status_code == 400


def test_preflight_shows_the_argv_without_executing(client):
    client.post("/api/config", json={"adapter": "cli"})
    payload = client.get("/api/preflight", params={"chain": "sol", "address": "TOK",
                                                   "amount": 0.05}).json()
    assert payload["argv"][:3] == ["gmgn-cli", "trade", "buy"]
    assert payload["would_execute"] is False


# --- public demo -------------------------------------------------------------

def test_public_demo_is_read_only(client, monkeypatch):
    monkeypatch.setattr(app_module, "PUBLIC_DEMO", True)
    assert client.post("/api/config", json={"adapter": "cli"}).status_code == 403
    assert client.post("/api/buy", json={"chain": "sol", "address": "x", "amount": 0.05}).status_code == 403
    assert client.post("/api/mode", json={"mode": "LIVE", "confirm": True}).status_code == 403
    assert client.post("/api/settings", json={"chain": "sol", "reset": True}).status_code == 403


def test_public_demo_strips_position_data(client, monkeypatch):
    candidate = run_round(client)["candidates"][0]
    client.post("/api/buy", json={"chain": "sol", "address": candidate["address"], "amount": 0.05})
    monkeypatch.setattr(app_module, "PUBLIC_DEMO", True)
    assert run_round(client)["positions"] == []


def test_escape_alerts_reach_the_event_log(client, monkeypatch):
    candidate = run_round(client)["candidates"][0]
    client.post("/api/buy", json={"chain": "sol", "address": candidate["address"], "amount": 0.05})

    class Degrading:
        supports_live_orders = False
        name = "Degrading"

        def trending(self, command, limit=100):
            return []

        def token_price(self, address):
            return {"price": 1.0, "liquidity": 1_000.0}

        def token_security(self, address, **_):
            return {"honeypot": True, "mintable": True, "renounced": False,
                    "freezable": True, "sell_tax": 0.5, "top10_share": 0.99}

    monkeypatch.setattr(app_module, "get_adapter", lambda chain: Degrading())
    payload = run_round(client)
    assert payload["positions"][0]["escape"]["pulse"] is True
    assert any("exit now" in event["text"] for event in payload["events"])
