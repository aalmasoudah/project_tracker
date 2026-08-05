# Phase 15 Verification

Date: 2026-08-04

Status: Completed and verified

## Delivered Scope

- Permission-scoped, read-only AI project briefings in Arabic and English.
- Executive and operational detail with 7, 14, or 30-day evidence windows.
- Asynchronous Celery generation, bounded retry, stale-job recovery, and HTMX
  status updates.
- Groq Chat Completions with an approved GPT-OSS model allowlist, strict JSON
  Schema output, local schema/citation validation, and one bounded repair pass.
- Source citations, review attribution, safe audit events, completion
  notifications, daily quotas, token metrics, and feature/provider fail-closed
  configuration.
- Deterministic fake provider used only in development/testing.

## Acceptance Criteria

- Completed: authorized users can request a briefing only for a currently
  visible project.
- Completed: request, generation, viewing, source-link rendering, and review
  recheck current object-level access.
- Completed: generated output is a non-authoritative draft and cannot update
  projects, tasks, approvals, milestones, attendance, or other business data.
- Completed: every factual list item requires one or more allowlisted evidence
  citations; malformed or unsupported output fails safely.
- Completed: budgets, descriptions, comments, uploads, trainee/attendance data,
  credentials, raw audit data, and environment configuration are excluded from
  provider evidence.
- Completed: Arabic RTL and English LTR interfaces, translated messages, and
  responsive browser workflows are covered.
- Completed: request, completion, failure, and review actions are auditable;
  completion notifications are idempotent.

## Migrations Reviewed

- `apps/ai_briefings/migrations/0001_initial.py`: briefing/source models,
  indexes, lifecycle/review checks, and source uniqueness.
- `apps/ai_briefings/migrations/0002_seed_phase15_permissions.py`: grants AI
  permissions only to CEO, Executive Manager, Project Manager, and Supervisor.
- `apps/audit/migrations/0011_alter_auditevent_scope.py`: adds the dedicated
  AI-briefing audit scope.
- `apps/notifications/migrations/0003_remove_notification_notifications_category_valid_and_more.py`:
  adds the AI-briefing notification category and recreates category checks.

`python manage.py makemigrations --check --dry-run` reported `No changes
detected`.

## Automated Verification

- `ruff format --check apps config scripts tests manage.py`: 301 files already
  formatted.
- `ruff check apps config scripts tests manage.py`: passed.
- Scoped `mypy` over application/config/scripts and Phase 15/notification
  tests: passed across 194 source files.
- `pytest -m "not browser" -q`: 170 passed, 15 deselected.
- `pytest -m browser -q`: 15 passed, 170 deselected.
- Focused Phase 11/15 unit and integration rerun: 24 passed.
- Focused Phase 15 browser rerun: 1 passed.
- `python manage.py check`: no issues.
- `python scripts/compile_messages.py`: Arabic message catalog compiled.

## Manual Verification

- Opened the running local application in Arabic and confirmed the Arabic
  company name, RTL document direction, translated login controls, and native
  Arabic form labels.
- At a 1280-pixel desktop viewport, the document and body widths matched the
  viewport and the centered authentication card stayed within bounds.
- At a 390 by 844 mobile viewport, RTL remained active, document width stayed
  at 390 pixels with no horizontal overflow, and the responsive card stayed
  inside the viewport.
- The Playwright suite exercised the authenticated Arabic mobile briefing
  request, completed cited result, internal source navigation, and explicit
  review workflow using PostgreSQL and the deterministic provider.

## Security Review

- Provider URL and models are fixed/allowlisted; no provider tools, arbitrary
  URLs, custom prompts, or external search are available.
- `GROQ_API_KEY` is environment-only and no credential is stored in source,
  briefing output, audit metadata, or failure messages.
- Prompt-injection text from the database is treated as untrusted evidence and
  cannot expand the data scope or trigger actions.
- Cross-project access fails closed; citations are linked only when the viewer
  can still access their underlying source.

## Limitations and Deployment Check

- A live Groq request was not executed because no deployment API key was used
  during verification. Before enabling the feature in staging, configure the
  secret, run the Celery worker and Redis, generate one Arabic and one English
  briefing with `openai/gpt-oss-120b`, inspect citations/token metrics, and
  confirm provider quota/timeout monitoring.
- Telegram/n8n delivery, portfolio-wide briefs, and attendance reporting are
  outside Phase 15 and require a separately approved privacy/security scope.

Recommended commit message: `feat: add cited Groq AI project briefings`
