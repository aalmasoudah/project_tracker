# Phase 5 Verification

Verified on 2026-07-27 against PostgreSQL and Python 3.13.

## Completed Criteria

- Project/course task creation, edit, list/filter, detail, archive, and
  restore.
- Three-level acyclic same-owner hierarchy with archive ordering.
- Multiple eligible assignees with exactly one active primary owner.
- Approved task statuses/transitions, blocking reason, dates, priorities, and
  non-negative two-decimal hour fields.
- Role- and object-scoped visibility for all seven predefined roles.
- Immutable comments and files, bilingual tags, end-dated relationships, and
  append-only task audit events.
- Private validated PDF/DOCX/XLSX/PPTX/PNG/JPEG uploads with authorized
  download routes.
- Project/course archive guards while active tasks remain.
- Complete Arabic/English UI, task search, RTL/LTR direction, and mobile
  layout verification.
- No dependencies, recurrence, approvals, watchers, notifications, or
  progress calculations were added.

## Migrations

- `audit.0004_alter_auditevent_scope`
- `tasks.0001_initial`
- `tasks.0002_seed_phase5_permissions`

The initial task migration was reviewed with `sqlmigrate`. Fresh PostgreSQL
test databases applied all migrations successfully.

## Executed Quality Gate

- `python scripts/update_messages.py`: 497 messages, 0 untranslated.
- `python scripts/compile_messages.py`: passed.
- `ruff format --check .`: passed.
- `ruff check .`: passed.
- `mypy .`: passed across 107 source files.
- `python manage.py check`: passed.
- `python manage.py check --deploy` with safe fictional production
  configuration: passed.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- `pytest -m "not browser" -q`: 57 passed, 5 deselected.
- `pytest -m browser -q`: 5 passed, 57 deselected.
- `docker compose config --quiet`: passed.
- `git diff --check`: passed.

## Browser and Manual-Equivalent Simulation

At a 390 × 844 mobile viewport:

1. An Arabic Project Manager created a project task with Arabic/English
   names, dates, estimated hours, one assignee, and one primary owner.
2. The Arabic task detail showed the assignee and stayed within the viewport.
3. The assigned Employee saw only the assigned task, changed it from To Do to
   In Progress, and entered actual hours.
4. The Employee added and retrieved an immutable Arabic comment.
5. The interface had no horizontal overflow.
6. Switching to English changed the document from Arabic RTL to English LTR.

The in-app development browser was signed out, so no real local account was
altered merely to repeat the isolated authenticated workflow.

## Security Review

- Direct URLs return not-found for users outside the approved object scope.
- Technical Admin receives no task-domain access.
- Task code and owner context are immutable.
- Manager task and assignment edits share an outer transaction.
- Uploads enforce size, extension, declared MIME type, file signatures, random
  storage keys, attachment disposition, and `nosniff`.
- Archived records are read-only and hard deletion is rejected.
- User content remains template-escaped; mixed-direction codes use bidi
  isolation.

## Limitations and Deferred Work

- Real production S3 transfer was not exercised because no production bucket
  credentials were supplied; production settings still fail closed without
  private S3 credentials, and local private-file authorization tests pass.
- Task dependencies, recurrence, approvals, watchers, notifications, overdue
  semantics, and progress calculations remain intentionally deferred.

Recommended commit message:

`feat: implement phase 5 tasks and collaboration`
