# System Acceptance Criteria

## Global Criteria

Every phase is complete only when:

- Its approved scope and acceptance criteria are implemented.
- Database migrations are reviewed and safe.
- Unit and integration tests pass.
- Required Playwright browser tests pass.
- Ruff formatting and linting pass.
- mypy passes.
- Django system checks pass.
- Manual verification is completed and recorded.
- Authorization and object-level access are tested.
- Security-relevant behavior is tested.
- Documentation is updated.
- The final Git diff contains no unrelated changes.
- No secrets, uploads, backups, or production data are committed.
- Every new user-visible feature has reviewed Arabic and English text,
  direction-aware layout, localized validation, and appropriate RTL/LTR
  browser coverage.
- Arabic content is stored, retrieved, filtered, exported, and rendered
  without corruption, clipping, unsafe direction changes, or loss of the
  original text.

## Engineering Foundation

- The application starts locally with PostgreSQL.
- A custom user model exists before the first application migration.
- Development, testing, and production settings are separate.
- A base authenticated Django page renders with Bootstrap and HTMX.
- The base page renders in Arabic RTL and English LTR, with a direction-aware
  language switch and local assets/fonts needed by both layouts.
- `/health/` reports application and database health without leaking secrets.
- Structured logging is configured.
- pytest, Ruff, mypy, Django checks, and CI are configured and passing.
- No business-domain features are implemented.

## Production Readiness

- Production uses `DEBUG=False`, HTTPS, secure cookies, and approved hosts.
- Staging and production use separate databases, storage, secrets, and
  fictional or anonymized staging data.
- Uploaded files use private S3-compatible object storage.
- Monitoring covers availability, errors, performance, workers, database
  capacity, backups, email failures, and abnormal authentication failures.
- Backup retention is documented, backups are encrypted, and a restoration
  test has succeeded.
- Role-based user acceptance testing is signed off.
- Arabic-language role-based acceptance testing and Arabic report rendering
  are signed off by an approved reviewer.
- Rollback, support, escalation, and operations procedures are documented.

## Requirement Status

These criteria are a system-level baseline. Detailed phase acceptance
criteria must be generated only after the unresolved business rules and
permission matrix are approved.
