# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The version-controlled record of the **transaction automation system for Daniel Yoon Realty** — a set of 13 Claude Routines and two Notion databases that run a real estate pipeline (leads → deals → closings → post-close nurture).

**The live system lives in Notion, not here.** This repo holds the durable design record. There is no application code, no build step, no test suite, and no lint configuration — do not go looking for them, and do not scaffold them for a docs change.

## Layout

- `docs/transaction-automation.md` — the system record: two-database architecture, all 13 routine definitions, the full Transactions schema, the ten system conventions, go-live order. **This is the primary artifact.** Read it before making any change related to the automation system.
- `CLAUDE.md`, `README.md` — this guidance and the repo intro.

The live counterparts in the Notion workspace (under **Daniel Yoon Realty — Operations**):
- Transactions DB: `https://app.notion.com/p/a72cdb9303ae4421b379105a7d455d9a` (data source `0cee9148-c040-42e6-ac35-5a231f0ffac0`)
- Lead Pipeline DB: data source `ef81006a-7e78-4253-a444-b22ad8cb47f7`
- 13 routine pages (verbatim prompts + test protocols), an Iteration Log, and a Go-Live Checklist as child pages of the Operations hub.

## The one rule that prevents real damage

**Schema changes to anything Zapier writes must be additive only.** Zapier Zaps write hardcoded select-option values into the Lead Pipeline database (`Status: New`, `Source: Country Club Guide`, …). Renaming or removing an existing option silently breaks live lead capture. Adding options is safe. The same caution applies to the Transactions `Stage` list: the routine prompts filter on exact stage names, so any Stage change requires re-auditing every routine's scope filter (the Iteration Log's Pass 2 entry in Notion shows how).

## Keeping the record in sync

When the live Notion system changes materially (schema, conventions, routine set, thresholds), update `docs/transaction-automation.md` in the same effort. The record drifting from the live system makes it worse than no record. Shared values are called out in the doc — e.g. the 10-showings price trigger lives in **both** L4 and L5 prompts and must change together.

## Git workflow

- **There is no `main`.** The default branch is `claude/add-claude-documentation-dfriw`; PRs base against it.
- Branch pattern: `claude/<feature-description>-<session-id>`. Pushes to other branch shapes are rejected (403).
- Conventional commits (`feat:`, `fix:`, `docs:`, `chore:` …). This repo's history is almost entirely `docs:`.
- Push with `git push -u origin <branch>`; on network failure retry with exponential backoff (2s/4s/8s/16s).
- Open PRs as drafts with a summary and test plan.

## Working conventions

- Make minimal changes; don't add features, files, or documentation beyond what was asked.
- Use Read/Edit/Write, Grep, and Glob rather than shell `cat`/`sed`/`grep`/`find`.
- The automation system's own conventions (draft-never-send, Activity Log vs Notes, fair housing on client-facing copy, the wire rule) are documented in `docs/transaction-automation.md` §"System conventions" — any content in this repo that feeds the live system inherits them.
