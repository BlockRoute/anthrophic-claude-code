# evaluate.md — Evaluation protocol (the fixed `prepare.py` analog)

**Do not edit this during an experiment run.** Changing the eval invalidates comparisons. Edit only between research phases, and reset the baseline when you do.

---

## Protocol

For each experiment, the agent runs **one simulated call per persona** (8 personas below = N=8 calls). For noise reduction, run the full persona set **3 times with seed variation** (N=24 total) and report the mean.

### Simulation turn structure

1. Load the current `docs/expired-listing-script.md` as the AGENT's playbook.
2. Load ONE persona from the list below as the PROSPECT.
3. Spin up a two-agent dialogue:
   - **AGENT LLM:** must use the script's opener verbatim, then follow the script's structure but adapt wording to prospect responses. May not invent facts outside the script.
   - **PROSPECT LLM:** plays the persona. Independently decides each turn whether to hang up, push back, deflect, open up, or agree. Never told the outcome in advance. Temperature 0.8.
4. Terminate when the prospect hangs up, agrees to an appointment, or 15 turns elapse.
5. An **JUDGE LLM** (separate call, temperature 0) then scores the transcript.

### Judge rubric (output JSON)

```json
{
  "listened_past_30s": true,
  "meaningful_discovery": true,
  "appointment_set": false,
  "turns_survived": 9,
  "thats_right_moments": 1,
  "prospect_trust_0_10": 6,
  "guardrail_violation": null,
  "notes": "Prospect engaged on discovery but ask came too early — pushed back on timing not value."
}
```

Any `guardrail_violation` (TCPA, high-pressure, price argument) zeros the run.

### Scoring

- **E[APPT/100]** = (appointments_set / N) × (assumed connect rate 0.12) × 100
  - Baseline connect rate 12% is a constant across experiments — we're measuring script-quality lift on connected calls, then projecting to 100 dials.
- Report mean ± std across the 3 seed-varied passes.
- A variant **wins** if mean beats baseline mean by ≥0.5 absolute appointments/100 AND std does not inflate by >30%.

---

## Personas (fixed set — do not edit during a run)

### P1 — "Frustrated Fiona" (burned by last agent)
- 62, empty-nester, 4-bed colonial, listed $625k, expired after 94 DOM.
- Last agent was a neighbor-friend; stopped returning calls after week 3.
- Opening mood: exhausted, short. Will hang up fast if pitched.
- **Wins with:** accusation audit, "barely called you back" mirror, validation.

### P2 — "FSBO Frank"
- 55, tradesman, 3-bed ranch, listed $410k, expired, now planning to go FSBO.
- Believes agents are overpaid. Sharp, argumentative, respects directness.
- **Wins with:** real numbers on FSBO close rates, no-pressure frame, two paths ask.

### P3 — "Price-Anchored Pam"
- 47, relocating for job, 5-bed, listed $899k (comps support $780k), 60 DOM.
- Convinced the market is wrong, not her price. Blames agent's marketing.
- **Wins with:** agree-the-number-could-be-right, earn in-person comp review.

### P4 — "Re-lister Ron"
- 71, retiring, 3-bed rambler, listed $525k, expired, already re-signed verbally with prior agent.
- Loyal, relationship-driven. Will bail if script feels transactional.
- **Wins with:** "how are you supposed to know" calibrated Q, respect for existing relationship.

### P5 — "Burnout Betty"
- 38, divorce-driven sale, 3-bed townhouse, listed $385k, expired, now "taking a break."
- Emotionally raw. Will hang up on energy mismatch.
- **Wins with:** labeled empathy first, "would it be ridiculous" low-stakes ask, no listing pitch.

### P6 — "Skeptical Sam"
- 49, engineer, 4-bed new-build, listed $740k, expired.
- Suspicious of all sales calls. Will test the agent: "how did you get my number?"
- **Wins with:** full transparency, permission to opt out, fast answer.

### P7 — "Market-Excuse Maya"
- 54, 4-bed in softening sub-market, listed $565k, expired after 78 DOM.
- Blames interest rates, news cycle. Feels the market "won't let her sell."
- **Wins with:** specific sub-market pending data, "what would change if…" calibrated Q.

### P8 — "Silent Steve"
- 66, widower, 3-bed, listed $490k, expired, low affect, barely speaks.
- Short answers. Will hang up on any dead air of his own doing.
- **Wins with:** labels (he rarely volunteers, so labeling for him works), mirrors on his few words.

---

## What a "connect" looks like (simulation convention)

Every simulated call starts with connection. The simulation measures what happens *after* hello. Dial-level connect rate (0.12) is held constant in the projection to isolate script quality.

## Re-basing

When `program.md` changes or a new persona is added, reset the baseline: re-run the current best script against the new eval 3 times and record the new baseline in `experiments/log.md`.
