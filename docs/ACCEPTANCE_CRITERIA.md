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

## Phase 15 AI Project Briefings

- Only an active CEO, Executive Manager, owning Project Manager, or assigned
  Supervisor can generate, read, or review a briefing inside current project
  visibility.
- Generation is asynchronous, bounded, idempotent, recoverable after an
  interrupted worker, and cannot block or modify core project workflows.
- Groq uses `openai/gpt-oss-120b` by default, permits only the approved 20B
  override, uses strict JSON Schema, and receives no tools.
- The evidence payload excludes budgets, descriptions, comments, files,
  trainee/attendance data, credentials, and raw audit metadata.
- Every factual list item has a locally validated citation to a currently
  permission-checked internal source.
- Arabic RTL and English LTR request/result/review flows pass automated and
  manual checks.
- Audit records and an idempotent in-app notification cover the request,
  completion/failure, and review lifecycle without storing prompts, responses,
  secrets, or raw provider errors in logs.

## Phase 16 CEO Telegram and n8n Executive Reports

- Only the exact configured active CEO username and Telegram chat can use the
  signed n8n integration; all other roles, chats, and anonymous calls fail
  without record discovery.
- Fixed commands asynchronously produce bounded Arabic current-task,
  overdue-task, and attendance reports without changing source records.
- The attendance PDF includes approved trainee names and attendance values but
  excludes phone/email/notes/files; Groq receives aggregates and no names.
- Requests require valid HMAC-SHA256, a fresh timestamp, a one-use nonce, a
  bounded known schema, and complete fail-closed production configuration.
- PDF links expire after ten minutes, download once, render in memory, and
  preserve Arabic RTL, Insight Projects branding, and Gregorian/Hijri dates.
- Critical task alerts are fingerprint-deduplicated, leased, retryable, and
  acknowledged by n8n before delivery is final.
- n8n workflow exports contain no credential values and successful/failed
  execution retention plus execution-progress storage are disabled.
- Audit/log metadata contains no trainee names, chat IDs, report bodies,
  provider payloads, tokens, or secrets.

## Phase 17 Agentic Project Recovery and Planning

- A predefined goal produces a bounded stored plan and dynamically selects at
  least two distinct allowlisted read tools.
- A safe structured observation materially influences the next selected step,
  and every factual statement or proposal cites an observed source.
- Only an explicitly reviewed completed run becomes same-project memory; a
  later run can recall and cite it while unreviewed memory is excluded.
- Every action remains a pending proposal until an authorized human approves
  it with a reason. The model cannot call a business write service.
- Approved execution is transactional and idempotent, rechecks current Phase
  17 and underlying domain permissions plus the before-state fingerprint, and
  never bypasses completion approval.
- A cited verification step reports the actual final state. Duplicate,
  rejected, stale, expired, forged, unauthorized, and revoked-access attempts
  produce no second or partial write.
- Step, token, time, request, and tool-result limits fail closed with safe
  codes. Provider timeouts retry only within the configured bound.
- Prompt injection and requests for shell, SQL, filesystem, web, arbitrary
  HTTP, credentials, files, trainees, attendance, or raw audit data cannot
  expand tools, scope, evidence, or actions.
- Arabic RTL/mobile and English LTR request, timeline, decision, memory, and
  verification flows pass automated and manual checks.
- The signed n8n reviewed-event flow enforces HMAC, freshness, replay
  protection, idempotency, and a human checkpoint; its export has no secrets.

## Requirement Status

These criteria are a system-level baseline. Detailed phase acceptance
criteria must be generated only after the unresolved business rules and
permission matrix are approved.
