# Transaction Automation — System Record

Version-controlled record of the Claude Routines transaction system built in Notion for Daniel Yoon Realty. The live system — databases, routine pages with verbatim prompts, iteration log, and go-live checklist — lives in the Notion workspace under **Daniel Yoon Realty — Operations**. This document is the durable reference for its architecture and schemas.

Built from the "Transaction Automation — Claude Routines Playbook", then hardened through three pre-go-live iteration passes (22 defects/gaps found and fixed; see the Iteration Log in Notion).

## Architecture

**State lives in Notion. Schedules drive the sweeps. Events fire via API.**

Two databases carry the whole pipeline (all price points, not just luxury):

| Database | Role | Data source ID |
|---|---|---|
| **Lead Pipeline** (renamed from Luxury Lead Pipeline) | Every lead, every source. Populated by Zapier (website forms) and B1 (phone/referral/portal). The relationship record. | `ef81006a-7e78-4253-a444-b22ad8cb47f7` |
| **Transactions** | Every deal, consult through closing. One row per transaction. Stage routes all routine logic. | `0cee9148-c040-42e6-ac35-5a231f0ffac0` |

## The 13 routines

### Scheduled
| Routine | Schedule | Job |
|---|---|---|
| Daily Transaction Sweep | Weekdays 6:45am ET | Deadline math on every active deal; RED/YELLOW/QUIET briefing with drafts attached |
| X1 Closing Week Runbook | Daily 7:15am ET | Acts when settlement ≤ 7 days out; chases only unconfirmed items until settled |
| L5 Price Reduction Analysis | Alt. Mondays 8:00am ET | Four-test underperformance screen; memo only on 2+ failures; hold means hold |
| X2 Post-Close Nurture | Mondays 9:00am ET | 14/90/365-day touches; referral asks, three per week max |
| L4 Weekly Seller Update | Fridays 3:00pm ET | Per-listing seller email drafts; showings mined from Gmail; price triggers |
| B2 Buyer Consult Prep | Weekdays 7:00pm ET | Prep sheet per next-day buyer meeting (Friday covers Sat/Sun/Mon) |

### API / event-fired
| Routine | Fires when | Job |
|---|---|---|
| B1 Lead Intake | Lead arrives | Score with lead-qualifier-agent, enrich Zapier's row, draft tiered first touch, SLA task |
| L1 Listing Dossier | Appointment booked | Pre-pitch research: facts, CMA band, market, objections, prep list; creates the deal row |
| L2 Listing Package | Seller commits | Fill four eXp forms via listing-form-filler; stage (never send) signing envelope |
| L3 Go-Live Kit | Photos back | MLS remarks, social, Canva, blog, sphere email; **sets List Date and Stage → Active** |
| B3 Tour Sheet | Tour list posted | Routed, timed, one printable page per property |
| B4 Offer Strategy | Buyer commits | Internal memo: value range, competitive read, three structures, gap math, walk-away number |
| B5 Inspection Triage | Report lands | inspection-report-reviewer skill; agent + client versions; repair request at row's posture; **Stage → Inspection** |

## Transactions schema

| Field | Type | Notes |
|---|---|---|
| Property | Title | Street address; buyer rows pre-ratification: `Client Name — target area` |
| Side | Select | Buyer / Seller. A "Both" client = two rows |
| Stage | Select | Lead → Consult → Active → Offer Out → Ratified → Inspection → Appraisal → Financing → Clear to Close → Closed; **Lost** = terminal, off-path, skipped by every routine |
| Client / Client Email | Text / Email | |
| Co-op Agent | Text | Name + email (parsed by sweep) |
| Ratified Date | Date | Anchors every contract deadline |
| Inspection / Financing / Appraisal deadlines, Settlement Date | Date | |
| List Date | Date | MLS go-live; **written only by L3**; anchors DOM for L4/L5 |
| List Price / Contract Price | Number ($) | List price while listed; contract price at ratification (safe: L4/L5 read only Active/Offer Out) |
| Lender / Title Co. | Text | |
| Water / Sewer | Select | Public / Well-Septic; drives B5 escalations; L1 fills from public record |
| Negotiating Posture | Select | Firm / Balanced / Concessive → B5's repair-request tone |
| Showings to Date | Number | L3 initializes 0; L4 increments weekly; feeds the 10-showings price trigger |
| Closing Confirmations | Multi-select | X1's memory; presence = confirmed |
| Post-Close Log | Multi-select | X2's memory; a logged milestone is never repeated |
| Notes | Text | **Human-only.** Routines read, never write |
| Last Swept | Date | Sweep's re-run guard; single-writer |

## System conventions (all routines inherit)

1. **Activity Log, not Notes** — routines log dated lines (`YYYY-MM-DD <id>: …`) to an "Activity Log" heading in the row's page body; Notes belongs to the human.
2. **Draft, never send** — no routine sends email, publishes, or releases a signing envelope (L2 explicitly bans DocuSeal `send_documents`).
3. **Stage written by three hands only** — L3 (Consult→Active), B5 (→Inspection, forward-only), the human for everything else. Never backwards.
4. **Degrade loudly, never silently** — missing connector/payload/source: do what works, name what was skipped at the top.
5. **Flag gaps, don't fill them** — blank beats invented, especially on anything signed; no estimated medians, no unsourced value figures.
6. **Fair housing on all copy** — describe property, never people; no schools-as-selling-point; no neighborhood-character language.
7. **Wire rule** — never draft, quote, forward, or paraphrase account/routing numbers, including ones found in the inbox; funds items get "verbal verification on an independently looked-up number" and nothing more.
8. **Cite comps** — every price figure names the comps it rests on.
9. **Idempotency** — every scheduled routine has a same-day re-run guard; every event routine dedupes or is harmless to re-run.
10. **Shared thresholds change together** — the 10-showings-no-offer trigger lives in both L4 and L5.

## Go-live order

Wave 1 (state layer proves itself): Sweep → B5 → L4 → B1. Wave 2, after two stable weeks: X1, X2, L1, L2, L3, L5, B2, B3, B4. Each routine's page carries the pass/fail test that must clear on a manual run before its trigger is attached.

Prerequisites: blank listing forms mirrored to Google Drive (L2), web search connector on L1/L3/L5/B1/B2/B3/B4/X2.

## Known integration points

- **Zapier** owns website form → Lead Pipeline + Lofty (webhook Zaps store the database by ID; the rename to "Lead Pipeline" did not affect them). B1 enriches Zapier's row rather than racing it.
- **Skills used:** `lead-qualifier-agent` (B1), `inspection-report-reviewer` (B5, and B3 reuses its Richmond red-flag table), `listing-form-filler` (L2).
- **No CMA skill exists yet** — L1, B4, L5 each run comps inline with deliberately different windows; a future `cma-report-builder` skill would keep them coherent.
