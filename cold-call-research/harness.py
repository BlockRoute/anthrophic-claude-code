"""
Autoresearch-style evaluation harness for the expired-listing cold-call script.

Runs N personas x M seeds of a simulated two-agent dialogue (AGENT playing the
real-estate agent from the script, PROSPECT playing a named persona), then
scores each transcript with a JUDGE model and aggregates to the autoresearch
metric E[APPT/100].

Usage:
    # from the cold-call-research/ directory
    export ANTHROPIC_API_KEY=sk-ant-...
    python harness.py --experiment exp001 --script ../docs/expired-listing-script.md --seeds 3

The caller is expected to have already mutated `../docs/expired-listing-script.md`
with the variant under test (per the loop in README.md).

Model / caching:
- Uses claude-opus-4-7 with adaptive thinking throughout.
- AGENT system prompt (instructions + full script) is cached — one breakpoint.
  Reused across every turn of every call that uses the same script.
- PROSPECT system prompt (instructions + persona) is cached per persona —
  reused across the 3 seeds for that persona.
- JUDGE system prompt is cached — reused across all 24 judging calls.

Concurrency: all (persona x seed) calls run in parallel via asyncio.gather,
then all judges run in parallel after.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from personas import PERSONAS

MODEL = os.getenv("COLD_CALL_MODEL", "claude-opus-4-7")
MAX_TURNS = 15
CONNECT_RATE = 0.12  # constant from evaluate.md, used only in the projection

HANGUP_TOKEN = "[HANGUP]"
AGREED_TOKEN = "[AGREED]"

AGENT_SYSTEM_TEMPLATE = """You are a real estate agent making a live cold call to the seller of an expired listing. Your playbook is below — follow its structure but adapt wording naturally to what the prospect says.

Rules:
- Stay in character as a real, experienced agent. Never break character.
- Open with the exact verbatim opener from the script's stage 2.
- Keep each turn conversational — 1-3 short sentences. This is a phone call, not an essay.
- Use the objection handlers from the script when the prospect pushes back.
- Never invent facts outside the script (no made-up comps, no fake credentials).
- Never argue price on the phone — agree it could be right, earn the in-person meeting.
- Never use high-pressure closing language.
- Output ONLY your spoken words. No stage directions, no narration, no brackets.

<script>
{script}
</script>
"""

PROSPECT_SYSTEM_TEMPLATE = """You are roleplaying the following expired-listing seller. A real estate agent just cold-called you.

<persona>
{persona_description}
</persona>

Rules:
- Stay in character. React as this specific persona would, with their specific history and mood.
- Independently decide each turn: engage, push back, deflect, hang up, or agree.
- Short replies — 1-3 sentences. This is a real phone call, not a monologue.
- If the agent's opening or approach triggers your defenses (per your persona), you can hang up. To hang up, output EXACTLY and ONLY: {hangup}
- If the agent genuinely earns your interest and asks for a specific appointment that you decide to accept, output EXACTLY and ONLY: {agreed}
- Otherwise respond naturally in character.
- Never narrate. Only say what the prospect would say aloud.
"""

JUDGE_SYSTEM = """You evaluate simulated cold-call transcripts between a real estate agent and an expired-listing seller. Score objectively per the rubric. Output JSON only.

Definitions:
- listened_past_30s: true if the prospect engaged for 2+ prospect turns without hanging up in their first 2 turns
- meaningful_discovery: true if the prospect answered 2+ substantive open-ended questions about their listing experience (price, agent, what went wrong, frustration, what they'd do differently)
- appointment_set: true only if the transcript ends with the AGREED token
- turns_survived: count of prospect turns in the transcript (exclude the opening "Hello?")
- thats_right_moments: count of prospect responses expressing strong agreement ("that's right", "exactly", "yeah that's it", "you got it")
- prospect_trust_0_10: your estimate of the prospect's final trust level in the agent (0 = would block the number, 10 = enthusiastic)
- guardrail_violation: any agent turn that (a) misrepresented identity or data source, (b) used a high-pressure close like "just sign today", or (c) argued price on the phone. Pick the first violation type or "none".
- notes: 1-2 sentences naming what worked or failed — specific, not generic
"""


class JudgeScore(BaseModel):
    listened_past_30s: bool
    meaningful_discovery: bool
    appointment_set: bool
    turns_survived: int = Field(ge=0)
    thats_right_moments: int = Field(ge=0)
    prospect_trust_0_10: int = Field(ge=0, le=10)
    guardrail_violation: Literal["tcpa", "high_pressure", "price_argument", "none"]
    notes: str


@dataclass
class CallResult:
    persona_id: str
    persona_name: str
    seed: int
    outcome: Literal["hangup", "appointment", "timeout"]
    turns: int
    transcript: list[dict]
    score: JudgeScore | None
    error: str | None = None


def _extract_text(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""


async def run_call(
    client: anthropic.AsyncAnthropic,
    script_text: str,
    persona: dict,
    seed: int,
) -> tuple[list[dict], str, int]:
    agent_system = [
        {
            "type": "text",
            "text": AGENT_SYSTEM_TEMPLATE.format(script=script_text),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    prospect_system = [
        {
            "type": "text",
            "text": PROSPECT_SYSTEM_TEMPLATE.format(
                persona_description=persona["description"],
                hangup=HANGUP_TOKEN,
                agreed=AGREED_TOKEN,
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    opening = "Hello?"
    transcript: list[dict] = [{"speaker": "prospect", "text": opening}]
    agent_messages = [{"role": "user", "content": opening}]
    prospect_messages = [{"role": "assistant", "content": opening}]

    seed_hint = f"[seed={seed}]"

    for turn in range(MAX_TURNS):
        agent_resp = await client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=agent_system,
            messages=agent_messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            metadata={"user_id": f"agent-{persona['id']}-{seed}"},
        )
        agent_text = _extract_text(agent_resp)
        if not agent_text:
            agent_text = "(silence)"
        transcript.append({"speaker": "agent", "text": agent_text})
        agent_messages.append({"role": "assistant", "content": agent_text})
        prospect_messages.append({"role": "user", "content": agent_text})

        prospect_resp = await client.messages.create(
            model=MODEL,
            max_tokens=250,
            system=prospect_system,
            messages=prospect_messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            metadata={"user_id": f"prospect-{persona['id']}-{seed} {seed_hint}"},
        )
        prospect_text = _extract_text(prospect_resp)
        if not prospect_text:
            prospect_text = HANGUP_TOKEN

        transcript.append({"speaker": "prospect", "text": prospect_text})
        prospect_messages.append({"role": "assistant", "content": prospect_text})
        agent_messages.append({"role": "user", "content": prospect_text})

        if HANGUP_TOKEN in prospect_text:
            return transcript, "hangup", turn + 1
        if AGREED_TOKEN in prospect_text:
            return transcript, "appointment", turn + 1

    return transcript, "timeout", MAX_TURNS


async def judge_call(
    client: anthropic.AsyncAnthropic,
    transcript: list[dict],
    outcome: str,
    turns: int,
) -> JudgeScore:
    formatted = "\n".join(
        f"{t['speaker'].upper()}: {t['text']}" for t in transcript
    )
    user = (
        f"Transcript:\n\n{formatted}\n\n"
        f"Final outcome: {outcome} after {turns} prospect turns.\n\n"
        "Score the transcript."
    )
    resp = await client.messages.parse(
        model=MODEL,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": JUDGE_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user}],
        output_format=JudgeScore,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
    )
    if resp.parsed_output is None:
        raise RuntimeError("judge returned unparseable output")
    return resp.parsed_output


async def run_and_judge(
    client: anthropic.AsyncAnthropic,
    script_text: str,
    persona: dict,
    seed: int,
) -> CallResult:
    try:
        transcript, outcome, turns = await run_call(
            client, script_text, persona, seed
        )
        score = await judge_call(client, transcript, outcome, turns)
        return CallResult(
            persona_id=persona["id"],
            persona_name=persona["name"],
            seed=seed,
            outcome=outcome,
            turns=turns,
            transcript=transcript,
            score=score,
        )
    except Exception as e:
        return CallResult(
            persona_id=persona["id"],
            persona_name=persona["name"],
            seed=seed,
            outcome="timeout",
            turns=0,
            transcript=[],
            score=None,
            error=f"{type(e).__name__}: {e}",
        )


def aggregate(results: list[CallResult]) -> dict:
    valid = [r for r in results if r.score is not None]
    n = len(valid)
    if n == 0:
        return {"error": "no valid results", "raw_count": len(results)}

    apt = sum(1 for r in valid if r.score.appointment_set)
    listened = sum(1 for r in valid if r.score.listened_past_30s)
    discovery = sum(1 for r in valid if r.score.meaningful_discovery)
    violations = [
        r for r in valid if r.score.guardrail_violation != "none"
    ]

    e_appt_per_100 = (apt / n) * CONNECT_RATE * 100
    by_persona: dict[str, dict] = {}
    for r in valid:
        p = by_persona.setdefault(
            r.persona_id, {"name": r.persona_name, "runs": 0, "appts": 0, "turns_sum": 0}
        )
        p["runs"] += 1
        p["appts"] += int(r.score.appointment_set)
        p["turns_sum"] += r.score.turns_survived

    for p in by_persona.values():
        p["appt_rate"] = p["appts"] / p["runs"]
        p["avg_turns"] = p["turns_sum"] / p["runs"]

    return {
        "n_runs_valid": n,
        "n_runs_errored": len(results) - n,
        "E_appt_per_100": round(e_appt_per_100, 2),
        "p_listened_past_30s": round(listened / n, 3),
        "p_meaningful_discovery": round(discovery / n, 3),
        "p_appointment": round(apt / n, 3),
        "avg_trust_0_10": round(
            sum(r.score.prospect_trust_0_10 for r in valid) / n, 2
        ),
        "avg_turns_survived": round(
            sum(r.score.turns_survived for r in valid) / n, 2
        ),
        "guardrail_violations": len(violations),
        "by_persona": by_persona,
    }


async def run_experiment(
    experiment_id: str,
    script_path: Path,
    seeds: int,
    output_dir: Path,
) -> dict:
    if not script_path.exists():
        raise FileNotFoundError(f"script not found: {script_path}")
    script_text = script_path.read_text()

    client = anthropic.AsyncAnthropic()

    tasks = [
        run_and_judge(client, script_text, persona, seed)
        for persona in PERSONAS
        for seed in range(seeds)
    ]
    print(
        f"running {len(tasks)} simulated calls "
        f"({len(PERSONAS)} personas x {seeds} seeds) in parallel...",
        file=sys.stderr,
    )
    results = await asyncio.gather(*tasks)

    agg = aggregate(results)
    payload = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "script_path": str(script_path),
        "script_sha256": _sha256_file(script_path),
        "seeds": seeds,
        "aggregate": agg,
        "calls": [
            {
                "persona_id": r.persona_id,
                "persona_name": r.persona_name,
                "seed": r.seed,
                "outcome": r.outcome,
                "turns": r.turns,
                "error": r.error,
                "score": r.score.model_dump() if r.score else None,
                "transcript": r.transcript,
            }
            for r in results
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{experiment_id}.json"
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out_path}", file=sys.stderr)
    return payload


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _print_summary(payload: dict) -> None:
    agg = payload["aggregate"]
    print()
    print(f"=== {payload['experiment_id']} ===")
    print(f"script sha: {payload['script_sha256']}")
    print(f"runs: {agg.get('n_runs_valid', 0)} valid, "
          f"{agg.get('n_runs_errored', 0)} errored")
    if agg.get("n_runs_valid", 0) == 0:
        return
    print(f"E[APPT/100]            : {agg['E_appt_per_100']}")
    print(f"P(listen past 30s)     : {agg['p_listened_past_30s']}")
    print(f"P(meaningful discovery): {agg['p_meaningful_discovery']}")
    print(f"P(appointment | call)  : {agg['p_appointment']}")
    print(f"avg turns survived     : {agg['avg_turns_survived']}")
    print(f"avg trust 0-10         : {agg['avg_trust_0_10']}")
    print(f"guardrail violations   : {agg['guardrail_violations']}")
    print()
    print("by persona:")
    for pid, p in sorted(agg["by_persona"].items()):
        print(
            f"  {pid} {p['name']:<22} "
            f"appts {p['appts']}/{p['runs']}  "
            f"avg_turns {p['avg_turns']:.1f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="experiment id, e.g. exp001")
    parser.add_argument(
        "--script",
        default="../docs/expired-listing-script.md",
        help="path to the mutable script artifact",
    )
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument(
        "--output-dir",
        default="experiments/results",
        help="where to write the results JSON",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set")

    payload = asyncio.run(
        run_experiment(
            experiment_id=args.experiment,
            script_path=Path(args.script),
            seeds=args.seeds,
            output_dir=Path(args.output_dir),
        )
    )
    _print_summary(payload)


if __name__ == "__main__":
    main()
