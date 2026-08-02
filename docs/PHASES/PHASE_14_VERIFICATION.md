# Phase 14 Verification

Date: 2026-08-02

## Outcome

Phase 14 application scope is implemented and verified under decision 0019.
The system now provides permission-scoped audit viewing and sanitized CSV,
an archive center that reuses existing object permissions, safe operations and
recorded backup-status presentation, protected idempotent commands, and the
approved non-destructive retention inventory. No database-restore web action
or application hard-delete path was added.

## Acceptance Evidence

- Technical Admin can view/export only security and operations audit; CEO and
  Executive Manager can view/export only business audit. Direct cross-scope
  detail URLs return 404 and unauthorized roles receive 403.
- Audit filters use allowlisted scopes/actions/target types, a maximum 366-day
  range, safe metadata keys, no-store responses, and a 5,000-row CSV limit.
  CSV formula prefixes are neutralized and raw metadata/IP/personal fields are
  excluded from export.
- Archive management lists only record types already restorable by the actor.
  Executive Manager receives supported global business records, Project
  Manager receives managed records and task tags, and Technical Admin receives
  departments. Existing restore confirmation views revalidate object scope.
- The Technical Admin operations page reports only application/database state,
  recorded backup/restoration-test freshness, recovery targets, and retention
  policy. It contains no secrets, topology, record counts, backup contents, or
  restore action.
- `record_backup_status` checks the configured environment, defaults to
  dry-run, requires an exact confirmation before recording, rejects future
  timestamps, and is idempotent. `retention_inventory` reports exact protected
  model counts, always has zero deletion candidates, has no deletion mode, and
  requires confirmation to record its safe summary.
- Arabic has 1,008 translated messages with zero untranslated entries. Phase
  14 pages use RTL Arabic and LTR English, localized validation/action labels,
  Asia/Riyadh time, and Gregorian/Umm al-Qura Hijri dates with Western digits.

## Migrations

- `audit.0009_phase14_audit_permissions_indexes`: adds the operations scope,
  four explicit audit view/export permissions, and scope/action timestamp
  indexes.
- `audit.0010_seed_phase14_audit_permissions`: grants Technical Admin
  security/operations audit and CEO/Executive Manager business audit.
- `operations.0001_initial`: adds only an unmanaged permission anchor; no
  operations data table is created.
- `operations.0002_seed_phase14_permissions`: grants the approved safe-status
  and archive-center permissions.

All four migrations were reviewed, applied successfully to the local
PostgreSQL database, and passed migration-drift checks.

## Automated Verification

- `pytest -q -m "not browser"`: 155 passed, 14 deselected.
- `pytest -q -m browser`: 14 passed, 155 deselected.
- Focused Phase 14 unit/integration suite: 9 passed.
- Focused Phase 14 Playwright suite: 1 passed.
- `ruff format --check .`: 276 files already formatted.
- `ruff check .`: passed.
- `mypy apps config`: 171 source files passed.
- `manage.py check`: passed.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- `manage.py check --deploy` with fictional production configuration and HSTS:
  no issues.
- Production `collectstatic --clear --noinput`: 142 files copied and 702
  post-processed; generated output was removed after verification.
- Translation extraction/compilation: 1,008 messages, zero untranslated.

## Manual and Security Verification

- Chrome/Playwright at a 390-by-844 viewport completed the Arabic audit filter,
  sanitized CSV download, archived-department discovery, and operations-status
  workflow; the audit table remains contained in a horizontal responsive
  region. Language switching then verified English LTR.
- Development `record_backup_status` dry-run printed its exact environment,
  kind, status, and timestamp and created no event.
- Development `retention_inventory` reported every protected model,
  `deletion_candidates=0`, `policy=indefinite`, and confirmed that no deletion
  mode exists. It changed no data.
- Tests cover forged scopes/record types, cross-scope audit IDs, unauthorized
  direct URLs, metadata redaction, CSV formula injection, excessive ranges,
  command environment mismatch, wrong confirmation, future timestamps,
  idempotency, and the absence of a web restore route.

## Limitations and Production Gates

- No real backup was created or restored. Provider account/region, named
  infrastructure owner and contacts, alert routes, and an isolated staging
  restoration exercise remain required before production launch.
- The application can record safe backup/restoration verification supplied by
  an authorized infrastructure operator; it cannot independently verify a
  provider backup and intentionally cannot restore one.
- Application data retention is indefinite. Any future deletion, legal-hold
  exception, or personal-data export requires a new approved decision.

Recommended commit message: `feat: complete phase 14 admin audit operations`
