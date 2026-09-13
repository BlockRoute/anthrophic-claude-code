import sys
from pathlib import Path

import pytest

AITRADER = Path(__file__).resolve().parents[1] / "aitrader"
sys.path.insert(0, str(AITRADER))


@pytest.fixture(autouse=True)
def isolated_outputs(tmp_path, monkeypatch):
    """Keep every test off the real outputs/ and ~/.config/gmgn/.env."""
    import store

    monkeypatch.setattr(store, "OUTPUTS_DIR", tmp_path)
    monkeypatch.setattr(store, "POSITIONS_PATH", tmp_path / "positions.json")
    monkeypatch.setattr(store, "DECISIONS_PATH", tmp_path / "trade_decisions.jsonl")
    monkeypatch.setattr(store, "TRENDING_CMDS_PATH", tmp_path / "trending_cmds.json")
    monkeypatch.setattr(store, "RISK_STATE_PATH", tmp_path / "risk_state.json")
    monkeypatch.setattr(store, "ENV_PATH", tmp_path / "env")
    yield
