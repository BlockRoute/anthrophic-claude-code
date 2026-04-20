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

Open a fresh Claude session and give it:

> Read `cold-call-research/program.md`, pick the next un-run experiment in `cold-call-research/experiments/log.md`, apply the mutation to `docs/expired-listing-script.md`, run the evaluation in `cold-call-research/evaluate.md` against all 8 personas, and log the result. If it beats baseline, keep it. Otherwise revert.

## Guardrails

- Agent only mutates `docs/expired-listing-script.md`. Nothing else.
- One hypothesis per round. No compound mutations.
- Never skip the eval — "it reads better" is not evidence.
- All experiments (wins and losses) go in the log. Losses are data.
