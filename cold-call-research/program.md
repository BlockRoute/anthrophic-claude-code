# program.md — Research direction for the expired-listing cold-call script

**This file is human-edited.** It tells the iterating agent where to focus, what to optimize, and what not to touch. Keep it short; agents read it every round.

---

## Primary metric

**Expected appointments set per 100 dials (E[APPT/100])** under the simulation protocol in `evaluate.md`.

This decomposes into three sub-metrics the agent should watch:

1. **P(listen past 30s | connect)** — opener strength
2. **P(meaningful discovery | past 30s)** — discovery depth (3+ calibrated Q's answered)
3. **P(yes to appointment | meaningful discovery)** — ask conversion

E[APPT/100] ≈ 100 × connect_rate × (1) × (2) × (3). The agent optimizes the product, not any single term.

## Secondary metrics (tiebreakers only)

- Average turns survived per connect (proxy for talk time)
- "That's right" moments per call (Voss earned-agreement signal)
- Persona-reported trust (0–10) in the post-call rating step

## Guardrails (do not violate)

1. **TCPA / honesty:** never instruct the agent to misrepresent identity, source of number, or fabricate rapport. The opener must disclose cold-call status and permission to opt out.
2. **No high-pressure close.** Anything that reads as "just sign today" is auto-rejected.
3. **No price argument on the phone.** Earn the appointment; present data in person.
4. **One mutation per experiment.** No compound changes.
5. **Keep the script scannable.** Max 250 lines of core script (objection handlers + delivery notes do not count).
6. **The mutable file is `docs/expired-listing-script.md`. Nothing else.**

## What to try (in priority order)

1. **Opener variants** — the biggest lever. Current baseline: pattern-interrupt + 30s exit + "Fair?" close. Test alternatives: NEPQ-style neutral problem-awareness open, peer-proof open, question-first open.
2. **Accusation audit placement** — currently stage 3. Test: inline with opener vs. after first mirror.
3. **Discovery question ordering + count** — currently 5 Q's. Test 3, 5, 7.
4. **Ask framing** — "20 min at kitchen table" vs. "15 min market read" vs. "Zoom walkthrough."
5. **Objection handler tone** — calibrated Q's ("how are you supposed to…") vs. story-based ("a seller last week…").
6. **VM sequence ordering** — test putting the permission-close VM at #2 instead of #3.

## What not to try (yet)

- Scripts for other lead types (FSBO-cold, circle-prospecting, past-client). Out of scope.
- Dialer/CRM integration. Out of scope.
- Multi-language variants. Revisit after English version plateaus.

## Stopping rule

Stop iterating on a dimension when 3 consecutive experiments on that dimension fail to beat baseline by >1 appointment per 100 dials. Move to the next priority.
