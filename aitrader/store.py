"""Local persistence: credentials, per-chain trending commands, positions, decision log."""

import json
import os
import threading
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_DIR / "outputs"
ENV_PATH = Path.home() / ".config" / "gmgn" / ".env"

POSITIONS_PATH = OUTPUTS_DIR / "positions.json"
DECISIONS_PATH = OUTPUTS_DIR / "trade_decisions.jsonl"
TRENDING_CMDS_PATH = OUTPUTS_DIR / "trending_cmds.json"
RISK_STATE_PATH = OUTPUTS_DIR / "risk_state.json"

CHAINS = ("sol", "bsc", "base", "eth")

DEFAULT_TRENDING_CMD = {
    "sol": "gmgn-cli market trending --chain sol --timeframe 5m --limit 100",
    "bsc": "gmgn-cli market trending --chain bsc --timeframe 5m --limit 100",
    "base": "gmgn-cli market trending --chain base --timeframe 5m --limit 100",
    "eth": "gmgn-cli market trending --chain eth --timeframe 5m --limit 100",
}

_lock = threading.Lock()


def _read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


# --- credentials -------------------------------------------------------------

def read_env():
    """Parse ~/.config/gmgn/.env into a dict. Missing file yields {}."""
    values = {}
    try:
        text = ENV_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env(updates):
    """Merge updates into the .env file, then chmod 600. Empty string deletes a key."""
    with _lock:
        values = read_env()
        for key, value in updates.items():
            if value == "":
                values.pop(key, None)
            else:
                values[key] = str(value)
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        body = "".join(f"{k}={v}\n" for k, v in sorted(values.items()))
        ENV_PATH.write_text(body, encoding="utf-8")
        os.chmod(ENV_PATH, 0o600)
    return values


# --- per-chain trending commands --------------------------------------------

def get_trending_cmd(chain):
    overrides = _read_json(TRENDING_CMDS_PATH, {})
    return overrides.get(chain) or DEFAULT_TRENDING_CMD[chain]


def set_trending_cmd(chain, command):
    with _lock:
        overrides = _read_json(TRENDING_CMDS_PATH, {})
        overrides[chain] = command
        _write_json(TRENDING_CMDS_PATH, overrides)
    return command


def reset_trending_cmd(chain):
    with _lock:
        overrides = _read_json(TRENDING_CMDS_PATH, {})
        overrides.pop(chain, None)
        _write_json(TRENDING_CMDS_PATH, overrides)
    return DEFAULT_TRENDING_CMD[chain]


# --- positions ---------------------------------------------------------------

def load_positions():
    return _read_json(POSITIONS_PATH, {})


def save_positions(positions):
    with _lock:
        _write_json(POSITIONS_PATH, positions)


# --- risk state --------------------------------------------------------------

def load_risk_state():
    return _read_json(RISK_STATE_PATH, {})


def save_risk_state(state):
    with _lock:
        _write_json(RISK_STATE_PATH, state)


# --- append-only decision log ------------------------------------------------

def log_decision(event, payload):
    record = {"ts": time.time(), "event": event}
    record.update(payload)
    with _lock:
        DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DECISIONS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def tail_decisions(limit=200):
    try:
        lines = DECISIONS_PATH.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
