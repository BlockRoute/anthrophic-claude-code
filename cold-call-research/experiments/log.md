# Experiment log

Newest at the top. Every experiment — win or loss — gets an entry. Losses are data.

Entry template:

```
## ExpNNN — <one-line hypothesis>
- Date:
- Author:
- Dimension: opener | accusation_audit | discovery | ask | objection | vm | cadence | delivery
- Mutation (diff summary):
- Seed runs: 3
- Baseline E[APPT/100]: X.X ± X.X
- Variant  E[APPT/100]: X.X ± X.X
- Sub-metrics (variant vs baseline): listen_30s / discovery / ask_yes
- Result: WIN | LOSS | INCONCLUSIVE
- Kept? yes/no
- Notes:
```

---

## BASELINE — v2 (current `docs/expired-listing-script.md`)
- Date: 2026-04-20
- Description: Pattern-interrupt opener + accusation audit + 5-Q calibrated discovery + mirrors/labels + 2-option ask + 7 objection handlers + 3-VM sequence + 5-touch cadence.
- Expected E[APPT/100]: TBD — run baseline 3× to seed before Exp001.
- Notes: This is the starting point. All experiments compare against it until a variant wins and replaces it.

---

# Queued experiments (pre-planned, un-run)

Run these in order. Each is a single, isolated mutation — matching autoresearch's "one change per experiment" discipline.

---

## Exp001 — Problem-awareness opener (Miner/NEPQ) instead of pattern-interrupt
- Dimension: opener
- Hypothesis: Neutral, curious-tone problem-awareness open lifts P(listen past 30s) on tired/skeptical personas (P1, P5, P6, P8) because it doesn't trigger the "sales call" alarm.
- Mutation: Replace the current opener with:
  > "Hey [First], Daniel Yoon — I realize you don't know me. I'm calling because I saw your home come off the market and I'm curious what you're planning to do from here — re-list, sit on it, or something else?"
- Prediction: +listen_30s, flat ask_yes on hot personas (P2, P3), overall +0.5 to +1.5 APPT/100.
- Risk: loses the explicit 30-second contract; may hurt on P2 (sharp/direct) who respect a frame.

## Exp002 — Accusation audit inline with opener
- Dimension: accusation_audit
- Hypothesis: Moving the accusation audit *into* the opener (rather than a separate stage) reduces time-to-disarm and lifts P(listen past 30s) across all personas.
- Mutation: Collapse stages 2 and 3 of the script into a single 2-sentence opener that combines the pattern interrupt + all three accusations ("20th agent, exhausted, here comes the pitch") in one breath.
- Prediction: +listen_30s on P1/P5/P8, flat elsewhere.
- Risk: breath control / too much in one turn; may sound rehearsed.

## Exp003 — Discovery compressed to 3 questions
- Dimension: discovery
- Hypothesis: 5 calibrated Q's is too many for low-affect personas (P8) and impatient ones (P2, P3); 3 captures 80% of the signal with higher completion.
- Mutation: Keep only Q1, Q3, Q5 from the discovery block. Drop Q2 and Q4.
- Prediction: +meaningful_discovery completion rate, possibly −depth on P1/P7 who like to vent.
- Risk: losing the venting-as-trust-building effect.

## Exp004 — Ask reframed as "15-minute market read, no listing pitch"
- Dimension: ask
- Hypothesis: A smaller, de-risked ask lifts P(yes) on break/burnout personas (P5, P8) without hurting hot personas.
- Mutation: Replace the "20 minutes at your kitchen table… pricing strategy" with:
  > "Give me 15 minutes at the house — no listing pitch, I promise. Just a current market read so whenever you *do* decide, you have the number and two fixes in hand. Saturday at 10 or Sunday at 2?"
- Prediction: +ask_yes on P1/P5/P8, −ask_yes on P2/P3 (they want the strategy pitch).
- Risk: under-commits on hot leads who wanted a real proposal.

## Exp005 — Peer-proof opener
- Dimension: opener
- Hypothesis: Leading with a specific, nearby pending re-list builds credibility before the accusation audit and lifts P(listen past 30s) across the board.
- Mutation: Replace opener with:
  > "Hey [First], Daniel Yoon at eXp. Quick reason I'm calling — a home almost identical to yours on [Nearby Street] went pending last week after it re-listed. I want to tell you what they changed, and then you can tell me to pound sand. Fair?"
- Prediction: +listen_30s especially on P3/P7 (data-anchored personas).
- Risk: if the nearby comp isn't real/fresh, you lose trust permanently. Script must gate this on pre-dial research confirming a valid nearby pending.

---

## Done experiments

(none yet)
