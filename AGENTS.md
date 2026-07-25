# AGENTS.md

## Mission

Build a secure, maintainable, and deployable internal project, course,
task, trainee-attendance, and completion-tracking system.

The application is a Django monolith backed by PostgreSQL.

## Required Reading

Before making changes, read:

1. `docs/SCOPE.md`
2. `docs/BUSINESS_RULES.md`
3. `docs/USER_ROLES.md`
4. `docs/WORKFLOWS.md`
5. `docs/ACCEPTANCE_CRITERIA.md`
6. `docs/LOCALIZATION.md`
7. The current approved file inside `docs/PHASES/`

Do not invent requirements or silently resolve conflicts. If documents
conflict, report the conflict and stop before making a business decision.

## Requirements Precedence

1. `docs/SCOPE.md`
2. `docs/BUSINESS_RULES.md`
3. `docs/USER_ROLES.md`
4. `docs/WORKFLOWS.md`
5. `docs/ACCEPTANCE_CRITERIA.md`
6. `docs/LOCALIZATION.md`
7. The current approved phase specification
8. The current Codex prompt

## Required Stack

- Django 5.2 LTS
- Python 3.13
- PostgreSQL in development, testing, staging, and production
- Django Templates
- Bootstrap 5
- HTMX
- pytest and pytest-django
- Playwright for critical browser workflows
- Ruff
- mypy
- Docker and Docker Compose
- Gunicorn
- Celery and Redis only when background processing is required
- S3-compatible storage in production
- First-class Arabic and English localization with RTL/LTR support

## Architecture

- Keep apps organized by business domain.
- Keep views thin.
- Use forms for input validation.
- Use services for multi-model workflows and business calculations.
- Use selectors or query helpers for complex reads.
- Use database constraints for rules that must never be violated.
- Use transactions for approvals, imports, and multi-step writes.
- Do not place business calculations in templates.
- Do not duplicate progress formulas.
- Avoid circular imports and generic utility dumping grounds.
- Separate development, testing, and production settings.
- Use environment variables for secrets and environment-specific settings.
- Use stable internal codes with translated Arabic/English labels; do not put
  localized labels in business logic.
- Preserve original Arabic text and use only approved normalization for
  identity, duplicate, sorting, and search behavior.

## Coding Standards

- Use type hints for public functions and service interfaces.
- Prefer small, cohesive functions and descriptive names.
- Avoid unnecessary abstractions and dependencies.
- Document business behavior that is not obvious.
- Follow established project patterns.
- Format and lint with Ruff.
- Do not suppress errors without justification.
- Every user-visible feature must include reviewed Arabic/English text and
  direction-aware tests.

## Security

- Never commit secrets, credentials, uploads, backups, or production data.
- Use Django password hashing and CSRF protection.
- Validate view-level and object-level permissions.
- Validate upload size, extension, and MIME type.
- Use random expiring attendance tokens and store hashes where possible.
- Log security-relevant actions.
- Never expose stack traces in production.
- Never use `DEBUG=True` outside local development.

## Database Rules

- Use PostgreSQL in all environments.
- Every model change requires a migration.
- Review migrations before applying them.
- Never edit deployed migrations without authorization.
- Add indexes for common filters and joins.
- Add constraints for critical data integrity.
- Prevent N+1 queries with `select_related` and `prefetch_related`.

## Business-Critical Rules

Task progress, course progress, project progress, approvals, attendance,
and cancelled-item behavior are defined in `docs/BUSINESS_RULES.md` and
may not be changed without approval.

## Scope Control

Implement only the current approved phase. Do not implement later phases,
redesign unrelated code, add speculative features, change formulas, remove
tests, or weaken validation.

## Required Workflow

Before editing:

1. Read the required documentation.
2. Inspect the code and tests.
3. Restate the current phase acceptance criteria.
4. List expected files and migrations.
5. Report conflicts, missing decisions, and risks.
6. Propose the smallest coherent implementation.

Before completion:

1. Run formatting.
2. Run linting.
3. Run type checking.
4. Run unit and integration tests.
5. Run required browser tests.
6. Run Django checks.
7. Review the Git diff.
8. Verify every acceptance criterion.

## Completion Report

Report completed and incomplete criteria, changed files, migrations,
commands, tests, manual verification, security considerations, limitations,
and a recommended commit message.

Never claim a test passed unless it was executed successfully.
