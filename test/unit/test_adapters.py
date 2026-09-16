import json

import pytest

from adapters import AdapterError, GmgnCliAdapter, LiveWriteBlocked, MockGMGN


def cli(runner=None, **kwargs):
    kwargs.setdefault("signing_key_present", True)
    return GmgnCliAdapter(chain="sol", runner=runner or (lambda argv: "{}"), **kwargs)


# --- mock --------------------------------------------------------------------

def test_mock_is_stable_within_a_seed():
    first = MockGMGN(chain="sol", seed=5).trending(limit=20)
    second = MockGMGN(chain="sol", seed=5).trending(limit=20)
    assert [row["address"] for row in first] == [row["address"] for row in second]


def test_mock_differs_per_chain():
    sol = {row["address"] for row in MockGMGN(chain="sol", seed=5).trending(limit=20)}
    bsc = {row["address"] for row in MockGMGN(chain="bsc", seed=5).trending(limit=20)}
    assert not sol & bsc


def test_mock_evm_addresses_look_evm():
    assert all(row["address"].startswith("0x") for row in MockGMGN(chain="base", seed=1).trending(limit=5))


def test_mock_refuses_to_sign_even_when_permitted():
    with pytest.raises(LiveWriteBlocked):
        MockGMGN(seed=1).place_order("buy", "addr", amount=0.1, live_writes_allowed=True)


def test_mock_paper_fill_is_marked_simulated():
    fill = MockGMGN(seed=1).place_order("buy", "addr", amount=0.1)
    assert fill["simulated"] is True and fill["tx_hash"] is None


# --- cli: command construction ----------------------------------------------

def test_trending_command_must_carry_the_expected_prefix():
    with pytest.raises(AdapterError, match="gmgn-cli market trending"):
        cli().trending("rm -rf /")


def test_trending_injects_chain_and_json():
    seen = {}

    def runner(argv):
        seen["argv"] = argv
        return "[]"

    cli(runner=runner).trending("gmgn-cli market trending --limit 10")
    assert seen["argv"][-4:] == ["--limit", "10", "--chain", "sol"] or "--chain" in seen["argv"]
    assert "--json" in seen["argv"]


def test_preflight_returns_argv_without_running_anything():
    def runner(argv):
        raise AssertionError("preflight must not execute")

    argv = cli(runner=runner).preflight_order("buy", "TOKEN", amount=0.05)
    assert argv[:4] == ["gmgn-cli", "trade", "buy", "TOKEN"]
    assert "--amount" in argv and "0.05" in argv


def test_order_commands_are_overridable():
    adapter = cli(commands={"buy": "mycli purchase {address} --size {amount} --chain {chain} --slippage {slippage}"})
    assert adapter.preflight_order("buy", "TOK", amount=1)[:2] == ["mycli", "purchase"]


# --- cli: write guards -------------------------------------------------------

def test_place_order_refuses_without_permission():
    def runner(argv):
        raise AssertionError("must not shell out")

    with pytest.raises(LiveWriteBlocked):
        cli(runner=runner).place_order("buy", "TOK", amount=0.1, live_writes_allowed=False)


def test_place_order_refuses_without_a_signing_key():
    with pytest.raises(AdapterError, match="no signing key"):
        cli(signing_key_present=False).place_order("buy", "TOK", amount=0.1, live_writes_allowed=True)


def test_place_order_returns_the_transaction_hash():
    payload = json.dumps({"data": {"order_id": "o1", "status": "filled",
                                   "tx_hash": "5xabc", "fill_price": 0.002}})
    fill = cli(runner=lambda argv: payload).place_order(
        "buy", "TOK", amount=0.1, live_writes_allowed=True)
    assert fill["tx_hash"] == "5xabc"
    assert fill["simulated"] is False
    assert fill["argv"][0] == "gmgn-cli"


# --- cli: output parsing -----------------------------------------------------

def test_parses_json_on_the_last_line_after_noise():
    noisy = "fetching...\nwarning: rate limited\n" + json.dumps({"data": {"price": 1.25}})
    assert cli(runner=lambda argv: noisy).token_price("TOK")["price"] == 1.25


def test_empty_output_is_an_error():
    with pytest.raises(AdapterError, match="no output"):
        cli(runner=lambda argv: "   ").token_price("TOK")


def test_non_json_output_is_an_error():
    with pytest.raises(AdapterError, match="not JSON"):
        cli(runner=lambda argv: "totally not json").token_price("TOK")


@pytest.mark.parametrize("payload,count", [
    ({"data": [{"symbol": "A"}, {"symbol": "B"}]}, 2),
    ({"data": {"rank": [{"symbol": "A"}]}}, 1),
    ([{"symbol": "A"}], 1),
    ({"unexpected": 1}, 0),
])
def test_row_extraction_handles_response_shapes(payload, count):
    rows = cli(runner=lambda argv: json.dumps(payload)).trending("gmgn-cli market trending")
    assert len(rows) == count


def test_security_flags_accept_string_booleans():
    payload = json.dumps({"data": {"is_honeypot": "1", "is_mintable": "0", "sell_tax": "0.05"}})
    security = cli(runner=lambda argv: payload).token_security("TOK")
    assert security["honeypot"] is True
    assert security["mintable"] is False
    assert security["sell_tax"] == 0.05


def test_missing_binary_reports_clearly():
    def runner(argv):
        raise FileNotFoundError()

    adapter = GmgnCliAdapter(chain="sol")
    with pytest.raises(AdapterError, match="not installed"):
        adapter._run_subprocess(["definitely-not-a-real-binary-xyz"])
