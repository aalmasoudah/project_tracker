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
  preserve Arabic RTL, Insight Tracker branding, and Gregorian/Hijri dates.
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

## Phase 19 Telegram AI Executive Assistant

- Only the exact configured active CEO/chat can create or retrieve a question.
- Arabic and English standalone executive questions produce bounded cited
  answers from current permission-scoped task/project/approval evidence.
- Deterministic local risk ranking limits evidence before Groq; strict schema
  and citation validation prevent unsupported factual output.
- Duplicate Telegram messages are idempotent, daily/evidence/token/time limits
  fail closed, and temporary provider failures retry only within the bound.
- Unknown commands, prompt injection, secret/personal-data requests, URLs,
  shell, SQL, web, files, attendance, and write requests reach no provider and
  disclose no record existence.
- n8n preserves all Phase 16 commands/alerts, contains no credentials, and
  sends the answer only to the configured private chat.
- Audit and logs contain safe lifecycle codes/counts only, never question or
  answer text, provider payloads, chat/message IDs, credentials, or raw errors.

## Phase 20 UI/UX Navigation, Progress, and Profiles

- The permission-aware desktop sidebar and mobile off-canvas menu mirror for
  Arabic/English, remain keyboard accessible, and expose no unauthorized link.
- Documented common destinations are reachable within three navigation
  interactions without removing security, confirmation, or approval steps.
- Shared buttons and footer remain readable, responsive, direction aware, and
  consistent with the approved Insight Tracker brand.
- Linear and circular indicators visibly present the exact existing Phase 6
  progress result, including empty and not-applicable states.
- The sidebar profile tab shows the current name, translated role, and active
  avatar or fallback without clipping or distortion.
- Avatar input is decoded, bounded, normalized, stored privately, served only
  after permission checks, and protected against malformed/deceptive uploads.
- Replacement and removal are transactional and audited, deactivate the prior
  display, and retain protected historical avatar evidence.

## Phase 21 Local LM Studio Inference and Controlled Fallback

- Local inference is disabled by default, limited to development, fixed to
  `http://127.0.0.1:1234/v1`, and cannot expose LM Studio through CORS, MCP,
  LAN, phone, n8n, Telegram, tunnel, staging, or production.
- Only logical model codes `qwen/qwen3.5-9b` and `openai/gpt-oss-20b` are
  accepted. One matching exact API model ID is pinned from `/v1/models`, and
  the artifact/reasoning pair passes the bilingual strict-JSON capability gate
  before enablement. Qwen requires `LM_STUDIO_REASONING_EFFORT=none`.
- Django independently validates every local schema, citation, identifier,
  permission, and object scope. Reasoning fields are discarded, and the model
  has no direct database, credential, tool, or business-service access.
- Telegram report summaries and executive answers make at most one Groq-to-
  local transition for an eligible transient failure and retain all existing
  command, privacy, evidence, citation, HMAC, idempotency, and delivery rules.
- A Recovery Agent run may transition once after a transient Groq failure,
  records safe transition metadata, stays pinned locally after the first valid
  local decision, and still satisfies the multi-tool, human-approval,
  transactional execution, stale-state, idempotency, and verification rules.
- Authentication, configuration, permission, security, unsafe-input, schema,
  citation, quota/budget, cancellation, stale, duplicate, and business-rule
  failures never trigger fallback. Local unavailability fails safely without
  oscillation or duplicate output.
- Usage remains bounded across retries and providers, effective local
  concurrency is one, and no missing usage is treated as zero.
- The user-operated launcher/readiness probe never silently downloads a model
  or prints secrets; Arabic/English, security, fallback, regression, and full
  quality-gate verification pass. The Project Recovery model constraint has a
  reviewed migration. Production remains Groq-only.

## Requirement Status

These criteria are a system-level baseline. Detailed phase acceptance
criteria must be generated only after the unresolved business rules and
permission matrix are approved.
