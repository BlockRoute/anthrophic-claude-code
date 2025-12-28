# CLAUDE.md - AI Assistant Development Guide

This document provides comprehensive guidance for AI assistants (like Claude) working with this repository. It covers codebase structure, development workflows, conventions, and best practices.

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Codebase Structure](#codebase-structure)
3. [Development Workflow](#development-workflow)
4. [Coding Conventions](#coding-conventions)
5. [Git Workflow](#git-workflow)
6. [Testing Guidelines](#testing-guidelines)
7. [Common Tasks](#common-tasks)
8. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Repository Overview

**Repository Name:** anthrophic-claude-code
**Purpose:** [To be defined as project develops]
**Primary Language:** [To be determined]
**Framework/Stack:** [To be determined]

### Key Information
- **Main Branch:** `main` (or `master`)
- **Development Branch Pattern:** `claude/<feature-name>-<session-id>`
- **Issue Tracker:** GitHub Issues
- **CI/CD:** [To be configured]

---

## Codebase Structure

```
anthrophic-claude-code/
├── .git/                  # Git repository metadata
├── src/                   # Source code (to be created)
├── test/                  # Test files (to be created)
├── docs/                  # Documentation (to be created)
├── scripts/               # Build and utility scripts (to be created)
├── .gitignore             # Git ignore patterns (to be created)
├── package.json           # Project dependencies (to be created if Node.js)
├── README.md              # Project documentation (to be created)
└── CLAUDE.md              # This file - AI assistant guide

```

### Directory Purposes

**`src/`** - Main source code directory
- Contains all application/library code
- Organized by feature or module
- Follow consistent naming conventions

**`test/`** - Test suites
- Unit tests
- Integration tests
- End-to-end tests
- Test utilities and fixtures

**`docs/`** - Documentation
- API documentation
- Architecture decision records (ADRs)
- User guides
- Development guides

**`scripts/`** - Automation scripts
- Build scripts
- Deployment scripts
- Database migrations
- Utility scripts

---

## Development Workflow

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd anthrophic-claude-code

# Install dependencies (adjust based on project type)
# npm install
# pip install -r requirements.txt
# cargo build
```

### Development Cycle

1. **Start with an Issue**
   - Create or identify a GitHub issue
   - Understand requirements fully before coding

2. **Create a Feature Branch**
   ```bash
   git checkout -b claude/<feature-name>-<session-id>
   ```

3. **Develop and Test**
   - Write code following conventions (see below)
   - Add/update tests for new functionality
   - Run tests locally before committing

4. **Commit Changes**
   ```bash
   git add <files>
   git commit -m "feat: descriptive commit message"
   ```

5. **Push and Create PR**
   ```bash
   git push -u origin claude/<feature-name>-<session-id>
   gh pr create --title "Title" --body "Description"
   ```

### Build Commands

```bash
# Development build (example - adjust based on project)
npm run dev

# Production build
npm run build

# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format
```

---

## Coding Conventions

### General Principles

1. **Simplicity First**
   - Write the simplest code that solves the problem
   - Avoid premature optimization
   - Don't add features not explicitly requested

2. **Code Quality**
   - Write self-documenting code with clear variable/function names
   - Add comments only when logic isn't self-evident
   - Keep functions small and focused (single responsibility)

3. **Error Handling**
   - Validate at system boundaries (user input, external APIs)
   - Trust internal code and framework guarantees
   - Don't add error handling for impossible scenarios

4. **Testing**
   - Write tests for new functionality
   - Update tests when modifying existing code
   - Aim for meaningful test coverage, not just high percentages

### Language-Specific Conventions

#### JavaScript/TypeScript
```javascript
// Use const by default, let when reassignment needed
const userName = "Claude";
let counter = 0;

// Use descriptive names
function calculateTotalPrice(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Use async/await over promises
async function fetchUserData(userId) {
  const response = await fetch(`/api/users/${userId}`);
  return response.json();
}
```

#### Python
```python
# Follow PEP 8
# Use snake_case for variables and functions
def calculate_total_price(items):
    return sum(item.price for item in items)

# Use type hints
def fetch_user_data(user_id: int) -> dict:
    response = requests.get(f"/api/users/{user_id}")
    return response.json()
```

### File Naming

- **Source files:** Use language conventions (camelCase.js, snake_case.py, PascalCase.tsx)
- **Test files:** Match source file with `.test` or `.spec` suffix
- **Config files:** Use lowercase with hyphens (eslint-config.js)

### Code Organization

- **One class/component per file** (unless closely related)
- **Group related functionality** in modules/packages
- **Separate concerns:** UI, business logic, data access
- **Use consistent import ordering:** stdlib, third-party, local

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

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(auth): add JWT token authentication"
git commit -m "fix(api): resolve race condition in user fetch"
git commit -m "docs: update API documentation for v2 endpoints"
git commit -m "test(user): add integration tests for user service"
```

### Push Guidelines

```bash
# Always push with -u for new branches
git push -u origin claude/<branch-name>

# Branch must start with 'claude/' and match session ID pattern
# If push fails with 403, verify branch name format

# Retry logic for network failures:
# - Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)
```

### Pull Request Guidelines

1. **Title:** Clear, descriptive summary of changes
2. **Description:**
   - Summary of what changed and why
   - Link to related issues
   - Test plan/testing done
   - Screenshots for UI changes
3. **Reviews:** Wait for approval before merging
4. **Checks:** Ensure all CI/CD checks pass

---

## Testing Guidelines

### Test Structure

```
test/
├── unit/           # Unit tests (isolated functions/classes)
├── integration/    # Integration tests (multiple components)
├── e2e/           # End-to-end tests (full user flows)
└── fixtures/      # Test data and mocks
```

### Writing Tests

```javascript
// Example unit test (Jest/Mocha style)
describe('calculateTotalPrice', () => {
  it('should return 0 for empty array', () => {
    expect(calculateTotalPrice([])).toBe(0);
  });

  it('should sum prices correctly', () => {
    const items = [{ price: 10 }, { price: 20 }];
    expect(calculateTotalPrice(items)).toBe(30);
  });
});
```

### Test Coverage Goals

- **New features:** 80%+ coverage
- **Bug fixes:** Add regression tests
- **Refactoring:** Maintain existing coverage
- **Critical paths:** Aim for 100% coverage

---

## Common Tasks

### Adding a New Feature

1. Read relevant existing code
2. Plan the implementation (use TodoWrite tool if complex)
3. Write tests first (TDD) or alongside implementation
4. Implement the feature minimally (no over-engineering)
5. Update documentation if needed
6. Commit with conventional commit message
7. Push and create PR

### Fixing a Bug

1. Understand the bug (read related code, reproduce if possible)
2. Write a failing test that demonstrates the bug
3. Fix the bug with minimal changes
4. Verify the test now passes
5. Check for similar bugs elsewhere
6. Commit and push

### Refactoring Code

1. Ensure tests exist for code being refactored
2. Make small, incremental changes
3. Run tests after each change
4. Don't mix refactoring with feature additions
5. Don't add new functionality during refactoring

### Updating Dependencies

1. Check changelog for breaking changes
2. Update one dependency at a time (for major versions)
3. Run full test suite
4. Update code if breaking changes exist
5. Test in development environment before merging

---

## AI Assistant Guidelines

### Before Making Changes

1. **Always read files before editing** - Never propose changes to code you haven't read
2. **Understand the context** - Read related files to understand patterns and conventions
3. **Check for existing solutions** - Search for similar implementations in the codebase
4. **Plan complex tasks** - Use TodoWrite tool for multi-step tasks (3+ steps)

### While Coding

1. **Follow existing patterns** - Match the style and structure already in use
2. **Make minimal changes** - Only change what's necessary for the task
3. **Don't over-engineer** - Avoid adding unnecessary features or abstractions
4. **Security first** - Watch for XSS, SQL injection, command injection, etc.
5. **Use appropriate tools:**
   - Use Read/Edit/Write for file operations (not bash cat/sed/echo)
   - Use Grep for searching code (not bash grep)
   - Use Glob for finding files (not bash find)

### Code Quality Checks

- [ ] No security vulnerabilities (SQL injection, XSS, command injection)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling at system boundaries only
- [ ] No unnecessary comments or docstrings
- [ ] No premature abstractions
- [ ] Tests added/updated for changes
- [ ] Follows existing code style
- [ ] No backwards-compatibility hacks for unused code

### Communication

1. **Be concise** - This is a CLI tool, keep responses focused
2. **No unnecessary emojis** - Only use if explicitly requested
3. **Reference code with line numbers** - Use `file:line` format
4. **Show progress** - Use TodoWrite to track multi-step tasks
5. **Ask when unclear** - Don't guess requirements, ask for clarification

### Git Operations

1. **Develop on feature branches** - Never push directly to main
2. **Use conventional commits** - Follow the format strictly
3. **Create meaningful PRs** - Include summary, test plan, and context
4. **Handle errors gracefully** - Retry network operations with backoff
5. **Verify before pushing** - Ensure tests pass and code builds

### What NOT to Do

❌ **Don't** create files unless absolutely necessary
❌ **Don't** add features not explicitly requested
❌ **Don't** create documentation files proactively
❌ **Don't** use bash for file reading/editing/searching
❌ **Don't** add comments explaining obvious code
❌ **Don't** create abstractions for one-time operations
❌ **Don't** add error handling for impossible scenarios
❌ **Don't** keep unused code with comments like "// removed"
❌ **Don't** guess at requirements - ask questions
❌ **Don't** mix refactoring with new features

### Efficiency Tips

1. **Parallel tool calls** - Run independent operations simultaneously
2. **Use specialized agents** - Task tool for complex exploration
3. **Read strategically** - Focus on relevant files, use search tools effectively
4. **Batch related changes** - Group related edits in single commits
5. **Trust the tools** - Don't verify operations that are guaranteed to work

---

## Project-Specific Notes

### Architecture Patterns

[To be documented as project develops]

### External Dependencies

[To be documented as dependencies are added]

### Environment Variables

[To be documented as needed]

```bash
# Example .env structure
# DATABASE_URL=postgresql://localhost/dbname
# API_KEY=your_api_key_here
# NODE_ENV=development
```

### Deployment

[To be documented when deployment process is established]

---

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

---

## Maintenance

**Last Updated:** 2025-12-28
**Document Version:** 1.0.0
**Maintainers:** Project team

### Change Log

- **2025-12-28:** Initial version created
  - Added comprehensive structure and guidelines
  - Established AI assistant best practices
  - Defined git workflow and conventions

---

## Questions or Issues?

If you encounter issues or have questions about this guide:

1. Check existing GitHub issues
2. Create a new issue with the `documentation` label
3. Tag with `question` if seeking clarification

This document should be updated as the project evolves and new patterns emerge.
