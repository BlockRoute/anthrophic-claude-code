# CLAUDE.md - AI Assistant Development Guide

This document provides guidance for AI assistants working with this repository. It covers the actual codebase structure, development workflows, and conventions.

---

## Repository Overview

**Repository Name:** anthrophic-claude-code
**Purpose:** Foundation repository for AI-assisted software engineering with Claude Code
**Status:** Early-stage — no source code, build system, or tests yet
**Main Branch:** `master`
**Development Branch Pattern:** `claude/<feature-name>-<session-id>`

---

## Current Codebase Structure

```
anthrophic-claude-code/
├── .git/              # Git repository metadata
├── .gitignore         # Comprehensive ignore patterns (multi-language)
├── CLAUDE.md          # This file — AI assistant guide
└── README.md          # Project overview and contributing guide
```

There are no `src/`, `test/`, `docs/`, or `scripts/` directories yet. Create them as needed when the project's language and framework are decided.

---

## .gitignore Coverage

The `.gitignore` is pre-configured for multiple ecosystems:
- **Node.js:** `node_modules/`, `.npm`, `.eslintcache`, yarn/pnpm files
- **Python:** `__pycache__/`, `.pytest_cache/`, `.tox/`, `.coverage`
- **Compiled languages:** `*.o`, `*.so`, `*.dll`, `target/`, `bin/`
- **Secrets:** `.env*`, `*.key`, `*.pem`, `secrets/`, `credentials/`
- **IDEs:** `.vscode/`, `.idea/`, `*.swp`
- **Build outputs:** `dist/`, `build/`, `out/`, `.next/`

---

## Git Workflow

### Branch Naming

```
claude/<feature-description>-<session-id>
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Push Protocol

```bash
# Always use -u for new branches
git push -u origin claude/<branch-name>

# Branch MUST start with 'claude/' and end with session ID
# 403 error = verify branch name format

# Network failure retry: up to 4 attempts with exponential backoff (2s, 4s, 8s, 16s)
```

### Pull Requests

- Short title (under 70 characters)
- Body includes: summary bullets, test plan, link to issues
- Wait for CI checks and review before merging

---

## Coding Conventions

### General Principles

- **Simplicity first** — write the simplest code that works
- **Minimal changes** — only change what's necessary for the task
- **No over-engineering** — no premature abstractions, no features not requested
- **Security aware** — validate at system boundaries, avoid injection vulnerabilities
- **Self-documenting** — clear names over comments; comment only non-obvious logic

### Language-Specific (apply when language is chosen)

- **JavaScript/TypeScript:** `const` by default, async/await, camelCase
- **Python:** PEP 8, snake_case, type hints

### Testing

- Write tests alongside new features
- Add regression tests for bug fixes
- Aim for meaningful coverage on critical paths

---

## AI Assistant Rules

### Tool Usage

- Use `Read`/`Edit`/`Write` for file operations (not bash `cat`/`sed`/`echo`)
- Use `Grep` for content search (not bash `grep`/`rg`)
- Use `Glob` for file search (not bash `find`/`ls`)
- Use `TodoWrite` for tasks with 3+ steps
- Run independent tool calls in parallel

### Before Editing

1. Always read files before modifying them
2. Search for existing patterns before introducing new ones
3. Understand context from related files

### What NOT to Do

- Don't create files unless necessary
- Don't add features not explicitly requested
- Don't add comments explaining obvious code
- Don't create abstractions for one-time operations
- Don't keep dead code with "// removed" comments
- Don't guess requirements — ask questions
- Don't mix refactoring with feature work

### Communication

- Be concise — this is a CLI tool
- Reference code as `file_path:line_number`
- No emojis unless requested
- Lead with the answer, not the reasoning

---

## Project-Specific Notes

No application code, dependencies, build system, environment variables, or deployment process exist yet. Update this section as the project develops.

---

## Maintenance

**Last Updated:** 2026-03-15
**Document Version:** 1.1.0

### Change Log

- **2026-03-15:** Updated to reflect actual repository state; removed placeholder sections; streamlined AI guidelines
- **2025-12-28:** Initial version created
