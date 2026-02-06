# CLAUDE.md - AI Assistant Development Guide

Guidance for AI assistants (like Claude) working with this repository. Covers codebase structure, development workflows, conventions, and best practices.

## Repository Overview

**Repository Name:** anthrophic-claude-code
**Purpose:** Foundation repository for AI-assisted software development with Claude Code. Serves as a template and guideline hub for projects developed using AI-powered workflows.
**Primary Language:** Language-agnostic (template supports JavaScript/TypeScript, Python, Rust, and others)
**Framework/Stack:** None currently configured -- to be chosen per project needs

### Key Information
- **Default Branch:** `claude/add-claude-documentation-dfriw` (no `main` branch exists yet)
- **Development Branch Pattern:** `claude/<feature-name>-<session-id>`
- **Issue Tracker:** GitHub Issues
- **CI/CD:** Not configured
- **Remote:** `BlockRoute/anthrophic-claude-code`

---

## Current Codebase Structure

This is a minimal template repository. No application code, build system, or dependencies exist yet.

```
anthrophic-claude-code/
├── .git/                  # Git repository metadata
├── .gitignore             # Comprehensive ignore patterns (multi-language)
├── CLAUDE.md              # This file - AI assistant guide
└── README.md              # Project overview and getting started
```

### What Exists

- **`.gitignore`** - Pre-configured for multiple ecosystems: Node.js, Python, Ruby, Java, Rust, plus IDE files, secrets, databases, and build outputs (149 lines)
- **`README.md`** - Project overview describing the AI-first development approach, contributing guidelines, and planned structure
- **`CLAUDE.md`** - This file

### Planned Directories (not yet created)

These directories should be created as needed when actual project development begins:

- **`src/`** - Application/library source code, organized by feature or module
- **`test/`** - Test suites (unit, integration, e2e, fixtures)
- **`docs/`** - API docs, architecture decision records, user/dev guides
- **`scripts/`** - Build, deployment, migration, and utility scripts

---

## Development Workflow

### Initial Setup

```bash
git clone <repository-url>
cd anthrophic-claude-code
```

No dependencies to install yet. When a project stack is chosen, add setup instructions here.

### Development Cycle

1. Create or identify a GitHub issue
2. Create a feature branch: `git checkout -b claude/<feature-name>-<session-id>`
3. Develop and test following the conventions below
4. Commit: `git add <files> && git commit -m "feat: descriptive message"`
5. Push: `git push -u origin claude/<feature-name>-<session-id>`
6. Create PR: `gh pr create --title "Title" --body "Description"`

### Build Commands

No build system is configured yet. When one is set up, document commands here:

```bash
# Placeholder examples (uncomment/replace when stack is chosen):
# npm run dev       # Development build
# npm run build     # Production build
# npm test          # Run tests
# npm run lint      # Lint code
# npm run format    # Format code
```

---

## Coding Conventions

### General Principles

1. **Simplicity First** - Write the simplest code that solves the problem. No premature optimization. No unrequested features.
2. **Self-Documenting Code** - Clear variable/function names. Comments only when logic isn't self-evident.
3. **Single Responsibility** - Small, focused functions.
4. **Boundary Validation** - Validate at system boundaries (user input, external APIs). Trust internal code.
5. **Meaningful Tests** - Write tests for new functionality. Update tests when modifying code. Aim for meaningful coverage, not percentages.

### Language-Specific Conventions

#### JavaScript/TypeScript
- `const` by default, `let` when reassignment needed
- `async/await` over raw promises
- Descriptive function and variable names

#### Python
- Follow PEP 8
- `snake_case` for variables and functions
- Type hints on function signatures

### File Naming
- **Source files:** Language conventions (camelCase.js, snake_case.py, PascalCase.tsx)
- **Test files:** Match source with `.test` or `.spec` suffix
- **Config files:** Lowercase with hyphens (eslint-config.js)

### Code Organization
- One class/component per file (unless closely related)
- Group related functionality in modules/packages
- Separate concerns: UI, business logic, data access
- Import ordering: stdlib, third-party, local

---

## Git Workflow

### Branch Naming

```
claude/<feature-description>-<session-id>
```

Examples:
- `claude/add-user-authentication-a1b2c`
- `claude/fix-login-bug-x9y8z`
- `claude/refactor-api-client-m5n6p`

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Push Guidelines

- Always use `git push -u origin <branch-name>`
- Branch must start with `claude/` and end with a matching session ID
- If push fails with 403, verify branch name format
- Retry network failures up to 4 times with exponential backoff (2s, 4s, 8s, 16s)

### Pull Requests

- Clear, descriptive title (under 70 chars)
- Body includes: summary of changes, linked issues, test plan
- Wait for approval before merging
- Ensure all CI/CD checks pass

---

## Testing Guidelines

No test framework is configured yet. When one is chosen, follow these guidelines:

### Recommended Structure
```
test/
├── unit/           # Isolated function/class tests
├── integration/    # Multi-component tests
├── e2e/            # Full user flow tests
└── fixtures/       # Test data and mocks
```

### Coverage Goals
- **New features:** 80%+ coverage
- **Bug fixes:** Add regression tests
- **Refactoring:** Maintain existing coverage
- **Critical paths:** 100% coverage

---

## AI Assistant Guidelines

### Before Making Changes

1. **Always read files before editing** - Never propose changes to unread code
2. **Understand context** - Read related files to learn patterns and conventions
3. **Search first** - Check for existing similar implementations
4. **Plan complex tasks** - Use TodoWrite for multi-step tasks (3+ steps)

### While Coding

1. **Follow existing patterns** - Match style and structure already in use
2. **Minimal changes** - Only change what's necessary
3. **No over-engineering** - No unnecessary features or abstractions
4. **Security first** - Watch for XSS, SQL injection, command injection
5. **Use proper tools:**
   - Read/Edit/Write for file operations (not bash cat/sed/echo)
   - Grep for searching code (not bash grep)
   - Glob for finding files (not bash find)

### Code Quality Checklist

- No security vulnerabilities (SQL injection, XSS, command injection)
- No hardcoded secrets or credentials
- Error handling at system boundaries only
- No unnecessary comments or docstrings
- No premature abstractions
- Tests added/updated for changes
- Follows existing code style
- No backwards-compatibility hacks for unused code

### What NOT to Do

- Don't create files unless absolutely necessary
- Don't add unrequested features
- Don't create documentation files proactively
- Don't use bash for file reading/editing/searching
- Don't add comments explaining obvious code
- Don't create abstractions for one-time operations
- Don't add error handling for impossible scenarios
- Don't keep unused code with "// removed" comments
- Don't guess at requirements -- ask questions
- Don't mix refactoring with new features

---

## Project Status

This repository is in its **initial template phase**. No application code, dependencies, build tools, CI/CD, or test frameworks have been configured. The repository currently provides:

- Development workflow guidelines and conventions
- Git branching and commit message standards
- AI assistant best practices
- A comprehensive `.gitignore` for multi-language development

As the project evolves, update this document with:
- Chosen language/framework/stack
- Actual build and test commands
- Architecture patterns and decisions
- External dependencies
- Environment variables
- Deployment procedures

---

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

---

**Last Updated:** 2026-02-06
**Document Version:** 1.1.0

### Change Log

- **2026-02-06:** Updated to reflect actual repository state
  - Replaced placeholder values with accurate information
  - Documented current file structure (3 files, no app code)
  - Clarified that no build system, test framework, or CI/CD is configured
  - Added project status section
  - Removed inaccurate references to nonexistent directories/files
  - Streamlined and deduplicated content
- **2025-12-28:** Initial version created
