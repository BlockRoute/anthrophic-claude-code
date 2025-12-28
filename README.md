# Anthropic Claude Code

A repository for Claude Code development and AI-assisted software engineering.

## About

This repository serves as a foundation for projects developed with Claude Code, Anthropic's AI-powered development assistant. It includes comprehensive guidelines and best practices for AI-assisted development workflows.

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Comprehensive guide for AI assistants working with this repository
  - Codebase structure and organization
  - Development workflows and conventions
  - Git workflow and branching strategy
  - Testing guidelines
  - AI assistant best practices

## Getting Started

This is currently a template repository. As you develop your project:

1. Update this README with project-specific information
2. Keep CLAUDE.md updated with architectural decisions and patterns
3. Follow the conventions outlined in CLAUDE.md
4. Use the git workflow described for consistent development

## Key Features

- **AI-First Development**: Optimized for Claude Code and AI-assisted development
- **Clear Conventions**: Well-documented patterns and guidelines
- **Comprehensive Documentation**: CLAUDE.md provides detailed guidance for AI assistants
- **Modern Workflows**: Git conventions, testing strategies, and best practices

## Contributing

When contributing to this repository:

1. Create a feature branch following the pattern: `claude/<feature>-<session-id>`
2. Follow conventional commit messages: `feat:`, `fix:`, `docs:`, etc.
3. Read CLAUDE.md for detailed development guidelines
4. Ensure tests pass before creating pull requests
5. Write clear, concise PR descriptions with test plans

## Development Workflow

```bash
# Create a feature branch
git checkout -b claude/your-feature-name-xxxxx

# Make your changes following CLAUDE.md guidelines

# Commit with conventional commits
git commit -m "feat: add new feature"

# Push to your branch
git push -u origin claude/your-feature-name-xxxxx

# Create a pull request
gh pr create --title "Add new feature" --body "Description of changes"
```

## Project Structure

```
anthrophic-claude-code/
├── CLAUDE.md          # AI assistant development guide
├── README.md          # This file
└── .git/             # Git repository
```

As the project grows, additional directories will be added:
- `src/` - Source code
- `test/` - Test suites
- `docs/` - Additional documentation
- `scripts/` - Build and utility scripts

## Resources

- [Claude Code Documentation](https://github.com/anthropics/claude-code)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

## License

[To be determined]

## Contact

For questions or issues, please create a GitHub issue in this repository.

---

**Note:** This repository is optimized for AI-assisted development with Claude Code. See CLAUDE.md for comprehensive guidelines.
