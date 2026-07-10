# CLAUDE.md - AI Assistant Development Guide

Guidance for AI assistants working in this repository. Keep this file to
conventions and directives a session can't derive from the codebase itself.

## Git Workflow

### Branch Naming

```
claude/<feature-description>-<session-id>
```

Examples: `claude/add-user-authentication-a1b2c`, `claude/fix-login-bug-x9y8z`.

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

Examples:
```
feat(auth): add JWT token authentication
fix(api): resolve race condition in user fetch
```

### Push Guidelines

- Always push new branches with `git push -u origin claude/<branch-name>`.
- Branch names must start with `claude/`; a 403 usually means the name format is wrong.
- Retry network failures up to 4 times with exponential backoff (2s, 4s, 8s, 16s).
- Never push directly to `main`. Wait for review before merging PRs.

## AI Assistant Directives

### Tool usage

- Use Read/Edit/Write for file operations — not bash `cat`/`sed`/`echo`.
- Use Grep for searching code — not bash `grep`.
- Use Glob for finding files — not bash `find`.

### Working practices

- Always read files before editing them.
- Make minimal changes — only what the task requires.
- Follow existing patterns already in the codebase.
- Watch for security issues (SQL injection, XSS, command injection).
- Plan multi-step tasks (3+ steps) with the TodoWrite tool.

### What NOT to do

- Don't create files unless necessary; don't create docs proactively.
- Don't add features that weren't requested.
- Don't add comments explaining obvious code.
- Don't add error handling for impossible scenarios.
- Don't keep unused code behind `// removed` comments.
- Don't mix refactoring with new features.
- Don't guess at requirements — ask when unclear.
