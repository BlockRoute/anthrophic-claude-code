# cold-call-research

An [autoresearch](https://github.com/karpathy/autoresearch)-style iteration loop for the expired-listing cold-call script.

## The shape

| autoresearch | cold-call-research |
|---|---|
| `prepare.py` (fixed) | `evaluate.md` — personas + judging protocol, unchanged by the agent |
| `train.py` (mutable) | `../docs/expired-listing-script.md` — the one artifact the agent modifies |
| `program.md` (direction) | `program.md` — research direction, metric, guardrails |
| 5-min training budget | N-persona simulation budget (default: 20 calls per variant) |
| `val_bpb` (lower better) | **expected appointments set per 100 dials** (higher better) |

## The loop

1. Agent reads `program.md` for research direction + constraints.
2. Agent reads the current `../docs/expired-listing-script.md` (the artifact).
3. Agent forms ONE hypothesis — a specific, minimal mutation.
4. Agent writes the mutation into the script.
5. Agent runs `evaluate.md` against all personas (LLM-judge simulation).
6. Agent logs hypothesis, diff, and score in `experiments/log.md`.
7. If score ≥ baseline: promote the mutation, update baseline. Else: revert.
8. Repeat.

## Running a round

Two ways — the Python harness is the primary path.

### Python harness (runnable eval loop)

Implements `evaluate.md` as a real two-agent simulation: Claude plays the agent, Claude plays each persona, a third Claude call judges the transcript and returns structured scores. 8 personas × 3 seeds × `(agent + prospect)` turns × 1 judge per call, all in parallel via `asyncio.gather`. Uses Opus 4.7 with adaptive thinking and prompt caching on the agent playbook + each persona system prompt.

```bash
cd cold-call-research
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=...  # or rely on your shell/env setup

# Smoke test first — 1 persona × 1 seed × 4-turn cap (use this to verify the loop works cheap):
python harness.py --experiment smoke --seeds 1

# Full experiment (8 personas × 3 seeds = 24 calls + 24 judges):
python harness.py --experiment exp001 --seeds 3
```

Each run writes `experiments/results/<experiment_id>.json` with: aggregate metrics, per-persona breakdown, full transcripts, JSON scores. The script's sha256 is recorded so you can prove *which* version of the playbook was tested.

> **Cost note:** a full run is ~24 calls × ~10 turns × 2 speakers + 24 judges ≈ 500+ Opus 4.7 requests. With adaptive thinking at `effort: medium`, budget a few dollars per experiment. Prompt caching keeps the agent system (script) and per-persona systems cheap on repeated turns/seeds. Set `COLD_CALL_MODEL=claude-sonnet-4-6` while tuning the harness if you want to iterate faster and cheaper — but re-baseline before trusting comparisons.

### Manual (no API calls — agent-driven loop)

Open a fresh Claude session and give it:

> Read `cold-call-research/program.md`, pick the next un-run experiment in `cold-call-research/experiments/log.md`, apply the mutation to `docs/expired-listing-script.md`, run `python cold-call-research/harness.py --experiment <id> --seeds 3`, and log the aggregate in `experiments/log.md`. If it beats baseline, keep it. Otherwise revert the script.

## Guardrails

- Agent only mutates `docs/expired-listing-script.md`. Nothing else.
- One hypothesis per round. No compound mutations.
- Never skip the eval — "it reads better" is not evidence.
- All experiments (wins and losses) go in the log. Losses are data.
- Never edit `evaluate.md` or `personas.py` during an experiment — changing the eval invalidates all prior comparisons. Only edit between research phases, and rebase the baseline.
