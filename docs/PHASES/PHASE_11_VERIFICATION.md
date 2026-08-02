# Phase 11 Verification

Verified on 2026-07-29.

## Acceptance Criteria

- Task assignment, current completion/attendance approval, task mention, and
  task deadline/overdue events create deduplicated, permission-safe in-app
  notifications.
- Owners can view and mark only their own notifications. Approval remains
  mandatory in-app; optional in-app and email channels follow persisted
  preferences.
- Notification titles/bodies are fixed generic Arabic/English content.
  Validated local target paths reveal no inaccessible business data and
  destination views recheck access.
- Multipart email selects the recipient's Arabic/English preference, renders
  RTL/LTR correctly, and uses console/in-memory/required production SMTP
  backends by environment.
- Redis, Celery worker, one-minute delivery dispatch, 08:00 Asia/Riyadh
  reminders, bounded retries, stale-work recovery, and safe operational
  delivery state are implemented.
- Technical Admin alone receives delivery-status access. SMS, chat, push, and
  escalation behavior are absent.
- Notifications, preferences, and delivery records are protected from normal
  hard deletion.

## Migrations

- `audit.0008_alter_auditevent_scope`
- `notifications.0001_initial`
- `notifications.0002_seed_phase11_permissions`

The migration plan was reviewed, migration drift was absent, and all three
migrations applied successfully to local PostgreSQL.

## Automated Verification

```text
python scripts/update_messages.py
  809 messages; 0 untranslated
python scripts/compile_messages.py
  Arabic catalog compiled
ruff format --check .
  218 files already formatted
ruff check .
  all checks passed
mypy .
  175 source files; no issues
python manage.py check
  no issues
python manage.py makemigrations --check --dry-run
  no changes
pytest -m "not browser"
  119 passed
pytest -m browser
  11 passed
```

Focused Phase 11 tests cover category policy, mandatory preferences,
deduplication, unsafe links, cross-user access, Arabic usernames in mentions,
Riyadh reminder timing, current approval recipients, attendance recipients,
email localization, all six Arabic plural forms, retry exhaustion, idempotent
sent-state replay, stale worker recovery, safe failure metadata, and
production fail-closed settings.

## Manual and Runtime Verification

- Docker Compose configuration validated.
- PostgreSQL and Redis containers reached healthy state; Redis returned
  `PONG`.
- A real Celery 5.6.3 solo worker connected to Redis, answered worker ping,
  registered all three notification tasks, consumed a scheduled reminder
  task, and reported success.
- Playwright verified the notification workflow at a 390 by 844 mobile
  viewport: Arabic RTL list, notification open/read, English LTR switch,
  mandatory approval control, and saved optional preferences.

## Security and Operational Review

- Stored content excludes record names, comments, email addresses, personal
  data, provider payloads, credentials, and raw exception messages.
- Event recipients are active assignees, current approvers, affected actors,
  or mentioned users with task visibility at event time.
- Email is queued only after the domain transaction commits; queue failure
  leaves a pending delivery for the dispatcher.
- Production rejects non-HTTPS application origins, non-Redis brokers,
  invalid sender addresses, disabled SMTP TLS, or missing SMTP credentials.
- A single Beat scheduler must run in each environment. Delivery monitoring,
  retry handling, and outage recovery are documented in `docs/OPERATIONS.md`.

## Limitations and Rollback

- SMTP cannot provide mathematically exact once-only delivery across a process
  crash after provider acceptance but before local sent-state commit. The
  application prevents normal replay after `sent`, uses one delivery record,
  and bounds every uncertain retry.
- Production provider selection, sender-domain authentication, monitoring
  thresholds, and retention/purge policy remain operational/Phase 14 work.
- Rollback must stop worker and Beat, drain or preserve compatible queued task
  payloads, revert code, and preserve notification/delivery evidence. The new
  protected tables must not be dropped after real use without an approved
  retention and recovery procedure.

Recommended commit message:

`feat: complete phase 11 notifications and background jobs`
