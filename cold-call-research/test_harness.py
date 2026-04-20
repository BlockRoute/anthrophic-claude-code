"""
Offline unit tests for the harness. Mocks the Anthropic client so no API
calls are made — verifies plumbing, loop termination, transcript shape,
cache-control placement, judge parsing, and aggregation math.

Run: python -m unittest test_harness -v
(requires `pip install -r requirements.txt` — the harness imports anthropic
and pydantic at module load.)
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from harness import (
    AGREED_TOKEN,
    HANGUP_TOKEN,
    MAX_TURNS,
    CallResult,
    JudgeScore,
    aggregate,
    judge_call,
    run_call,
)
from personas import PERSONAS, get_persona


def _text_response(text: str) -> MagicMock:
    """Build a minimal fake of what client.messages.create() returns."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


def _parse_response(score: JudgeScore) -> MagicMock:
    """Minimal fake of what client.messages.parse() returns."""
    resp = MagicMock()
    resp.parsed_output = score
    return resp


def _score(**overrides) -> JudgeScore:
    defaults = dict(
        listened_past_30s=True,
        meaningful_discovery=True,
        appointment_set=False,
        turns_survived=5,
        thats_right_moments=0,
        prospect_trust_0_10=5,
        guardrail_violation="none",
        notes="n/a",
    )
    defaults.update(overrides)
    return JudgeScore(**defaults)


def _result(**overrides) -> CallResult:
    defaults = dict(
        persona_id="P1",
        persona_name="Frustrated Fiona",
        seed=0,
        outcome="timeout",
        turns=5,
        transcript=[],
        score=_score(),
        error=None,
    )
    defaults.update(overrides)
    return CallResult(**defaults)


class TestSdkSurface(unittest.TestCase):
    """Fail fast if the SDK version doesn't expose what we need."""

    def test_async_client_has_parse_and_create(self):
        import anthropic

        client = anthropic.AsyncAnthropic(api_key="test")
        self.assertTrue(
            hasattr(client.messages, "parse"),
            "AsyncAnthropic.messages.parse missing — judge calls will fail",
        )
        self.assertTrue(hasattr(client.messages, "create"))


class TestPersonas(unittest.TestCase):
    def test_eight_personas(self):
        self.assertEqual(len(PERSONAS), 8)

    def test_unique_ids(self):
        ids = [p["id"] for p in PERSONAS]
        self.assertEqual(len(set(ids)), len(ids))

    def test_required_fields(self):
        for p in PERSONAS:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("description", p)
            self.assertTrue(len(p["description"]) > 100)

    def test_lookup(self):
        self.assertEqual(get_persona("P1")["name"], "Frustrated Fiona")
        with self.assertRaises(KeyError):
            get_persona("PX")


class TestRunCall(unittest.IsolatedAsyncioTestCase):
    async def test_hangup_terminates_turn_one(self):
        client = MagicMock()
        client.messages.create = AsyncMock(
            side_effect=[
                _text_response("Hey, is this Fiona?"),
                _text_response(HANGUP_TOKEN),
            ]
        )

        transcript, outcome, turns = await run_call(
            client, "FAKE SCRIPT", PERSONAS[0], seed=0
        )

        self.assertEqual(outcome, "hangup")
        self.assertEqual(turns, 1)
        # opening "Hello?" + 1 agent + 1 prospect = 3 entries
        self.assertEqual(len(transcript), 3)
        self.assertEqual(transcript[0]["speaker"], "prospect")
        self.assertEqual(transcript[0]["text"], "Hello?")
        self.assertEqual(transcript[1]["speaker"], "agent")
        self.assertEqual(transcript[2]["speaker"], "prospect")
        self.assertIn(HANGUP_TOKEN, transcript[2]["text"])

    async def test_agreed_terminates(self):
        client = MagicMock()
        client.messages.create = AsyncMock(
            side_effect=[
                _text_response("Opening"),
                _text_response("Go on, you have 30 seconds"),
                _text_response("OK, Saturday at 10 works"),
                _text_response(AGREED_TOKEN),
            ]
        )

        transcript, outcome, turns = await run_call(
            client, "FAKE SCRIPT", PERSONAS[0], seed=0
        )

        self.assertEqual(outcome, "appointment")
        self.assertEqual(turns, 2)

    async def test_timeout_on_max_turns(self):
        client = MagicMock()
        # every call returns chatty filler — neither side ever terminates
        client.messages.create = AsyncMock(return_value=_text_response("uh huh"))

        transcript, outcome, turns = await run_call(
            client, "FAKE SCRIPT", PERSONAS[0], seed=0
        )

        self.assertEqual(outcome, "timeout")
        self.assertEqual(turns, MAX_TURNS)
        # opening + MAX_TURNS * (agent + prospect)
        self.assertEqual(len(transcript), 1 + MAX_TURNS * 2)

    async def test_cache_control_on_agent_and_prospect_systems(self):
        client = MagicMock()
        client.messages.create = AsyncMock(
            side_effect=[
                _text_response("opener"),
                _text_response(HANGUP_TOKEN),
            ]
        )

        await run_call(client, "UNIQUE_SCRIPT_MARKER", PERSONAS[0], seed=0)

        calls = client.messages.create.call_args_list
        self.assertGreaterEqual(len(calls), 2)

        # call 0: AGENT — system must include the script and a cache breakpoint
        agent_system = calls[0].kwargs["system"]
        self.assertEqual(agent_system[0]["cache_control"], {"type": "ephemeral"})
        self.assertIn("UNIQUE_SCRIPT_MARKER", agent_system[0]["text"])

        # call 1: PROSPECT — system must include the persona and a cache breakpoint
        prospect_system = calls[1].kwargs["system"]
        self.assertEqual(prospect_system[0]["cache_control"], {"type": "ephemeral"})
        self.assertIn(PERSONAS[0]["description"][:40], prospect_system[0]["text"])

    async def test_adaptive_thinking_and_model_passed(self):
        client = MagicMock()
        client.messages.create = AsyncMock(
            side_effect=[
                _text_response("x"),
                _text_response(HANGUP_TOKEN),
            ]
        )

        await run_call(client, "s", PERSONAS[0], seed=42)

        kwargs = client.messages.create.call_args_list[0].kwargs
        self.assertEqual(kwargs["thinking"], {"type": "adaptive"})
        self.assertIn("model", kwargs)
        self.assertIn("messages", kwargs)

    async def test_empty_agent_response_does_not_crash(self):
        """If the model returns no text block, the loop inserts a placeholder
        and keeps going — it should not raise."""
        client = MagicMock()
        empty = MagicMock()
        empty.content = []  # no blocks at all
        client.messages.create = AsyncMock(
            side_effect=[empty, _text_response(HANGUP_TOKEN)]
        )

        transcript, outcome, _ = await run_call(client, "s", PERSONAS[0], seed=0)

        self.assertEqual(outcome, "hangup")
        # agent turn got the "(silence)" placeholder rather than raising
        self.assertEqual(transcript[1]["speaker"], "agent")
        self.assertEqual(transcript[1]["text"], "(silence)")


class TestJudgeCall(unittest.IsolatedAsyncioTestCase):
    async def test_judge_returns_parsed_score(self):
        client = MagicMock()
        expected = _score(
            appointment_set=True,
            turns_survived=7,
            guardrail_violation="none",
            notes="earned appt via accusation audit",
        )
        client.messages.parse = AsyncMock(return_value=_parse_response(expected))

        score = await judge_call(
            client,
            [{"speaker": "prospect", "text": "Hello?"}],
            "appointment",
            7,
        )

        self.assertEqual(score.turns_survived, 7)
        self.assertTrue(score.appointment_set)

        # verify the call wiring: system has cache breakpoint, output_format set,
        # transcript is in the user message
        kwargs = client.messages.parse.call_args.kwargs
        self.assertEqual(
            kwargs["system"][0]["cache_control"], {"type": "ephemeral"}
        )
        self.assertEqual(kwargs["output_format"], JudgeScore)
        self.assertIn("Hello?", kwargs["messages"][0]["content"])

    async def test_judge_raises_on_none_parsed(self):
        client = MagicMock()
        resp = MagicMock()
        resp.parsed_output = None
        client.messages.parse = AsyncMock(return_value=resp)

        with self.assertRaises(RuntimeError):
            await judge_call(client, [], "timeout", 0)


class TestAggregate(unittest.TestCase):
    def test_e_appt_math(self):
        # 2 appointments out of 4 valid runs → 50% × 12% connect × 100 = 6.0
        results = [
            _result(score=_score(appointment_set=True)),
            _result(score=_score(appointment_set=False)),
            _result(score=_score(appointment_set=True)),
            _result(score=_score(appointment_set=False)),
        ]
        agg = aggregate(results)
        self.assertEqual(agg["n_runs_valid"], 4)
        self.assertEqual(agg["E_appt_per_100"], 6.0)
        self.assertEqual(agg["p_appointment"], 0.5)

    def test_errored_runs_excluded_from_rates(self):
        results = [
            _result(score=_score(appointment_set=True)),
            _result(score=None, error="APIConnectionError: boom"),
        ]
        agg = aggregate(results)
        self.assertEqual(agg["n_runs_valid"], 1)
        self.assertEqual(agg["n_runs_errored"], 1)
        self.assertEqual(agg["p_appointment"], 1.0)

    def test_all_errored_returns_error_envelope(self):
        agg = aggregate([_result(score=None, error="x")])
        self.assertIn("error", agg)
        self.assertEqual(agg["raw_count"], 1)

    def test_guardrail_violations_counted(self):
        results = [
            _result(score=_score(guardrail_violation="high_pressure")),
            _result(score=_score(guardrail_violation="tcpa")),
            _result(score=_score(guardrail_violation="none")),
        ]
        agg = aggregate(results)
        self.assertEqual(agg["guardrail_violations"], 2)

    def test_per_persona_breakdown(self):
        results = [
            _result(
                persona_id="P1",
                persona_name="Fiona",
                score=_score(appointment_set=True, turns_survived=8),
            ),
            _result(
                persona_id="P1",
                persona_name="Fiona",
                score=_score(appointment_set=False, turns_survived=2),
            ),
            _result(
                persona_id="P2",
                persona_name="Frank",
                score=_score(appointment_set=True, turns_survived=10),
            ),
        ]
        agg = aggregate(results)

        p1 = agg["by_persona"]["P1"]
        self.assertEqual(p1["runs"], 2)
        self.assertEqual(p1["appts"], 1)
        self.assertEqual(p1["appt_rate"], 0.5)
        self.assertEqual(p1["avg_turns"], 5.0)

        p2 = agg["by_persona"]["P2"]
        self.assertEqual(p2["runs"], 1)
        self.assertEqual(p2["appts"], 1)
        self.assertEqual(p2["avg_turns"], 10.0)


if __name__ == "__main__":
    unittest.main()
