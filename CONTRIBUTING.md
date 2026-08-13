# Contributing to djaapp

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Development Setup

1. Fork and clone the repository
2. Install [Just](https://just.systems/) command runner
3. Install UV, Python 3.14, and Node.js 22
4. Run `just init`; it creates `.env` when needed, installs locked dependencies,
   and starts local PostgreSQL
5. Run `just verify` to execute the same core checks used before pull requests

Production monitoring, incident response, backup/restore, rollback, and
recovery verification follow the [Operations Runbook and Observability
Contract](docs/operations-runbook-and-observability.md).

## Code Style

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black-compatible)
- Use ruff for linting and formatting

## Testing

All contributions must include tests:

1. Write tests first (TDD approach)
2. Ensure all tests pass before submitting PR
3. Maintain or improve code coverage
4. Use pytest markers for test categorization

Pull requests are checked by CI. The test suite must pass and coverage must remain
at or above the configured 80% threshold. Run `just test-ci` locally to execute the
same test gate used by CI.

## Commit Messages

Use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build/tooling changes

## Pull Request Process

1. Update documentation for any changed functionality
2. Add tests for new features
3. Ensure CI passes (linting, tests)
4. Request review from maintainers
5. Address review feedback

## Questions?

Open an issue for questions or discussion.
