# Phase 16: CEO Telegram and n8n Executive Reports

Status: Completed and verified locally on 2026-08-04

## 1. Goal

Give the CEO a secure Arabic Telegram interface, orchestrated by n8n, for
current-task, overdue-task, and named trainee-attendance reports plus
retry-safe critical-task alerts.

## 2. Included Features

- Fixed Arabic Telegram commands for help, current tasks, overdue tasks, and
  trainee attendance.
- A narrow internal Django integration API called only by the approved n8n
  workflow.
- HMAC request signing, timestamp/nonce replay protection, exact chat binding,
  and a fixed active CEO account.
- Asynchronous Groq summaries from bounded aggregate evidence.
- Arabic branded PDFs containing the detailed source rows; trainee names and
  attendance values are approved only in the attendance PDF.
- Short-lived, one-time PDF downloads for n8n to forward to Telegram.
- Scheduled critical-task discovery with leased, acknowledged, retry-safe
  Telegram alert delivery.
- Safe audit events and operational metadata without chat identifiers,
  trainee names, report content, tokens, or provider payloads.
- An importable n8n workflow and an Arabic deployment/operation runbook.

## 3. Excluded Features

- Free-form chat, arbitrary prompts, arbitrary report filters, task changes,
  approvals, attendance corrections, or any other bot write to business data.
- Telegram access for any role other than the configured CEO.
- Trainee phone numbers, email addresses, attendance notes, trainer notes,
  uploaded files, comments, credentials, budgets, or raw audit data.
- Sending trainee names or individual attendance rows to Groq.
- Storing the Telegram bot token in Django or a raw Django signing secret in
  repository files, n8n workflow exports, logs, or audit metadata.

## 4. User Stories

- As the CEO, I can request an Arabic current-task PDF from Telegram.
- As the CEO, I can request an Arabic overdue-task PDF from Telegram.
- As the CEO, I can request an Arabic attendance PDF that includes trainee
  names and attendance values for the approved time window.
- As the CEO, I receive one retry-safe Arabic alert when a critical task enters
  the approved due/overdue window.
- As an operator, I can rotate Telegram, n8n, Django-signing, and Groq secrets
  independently.

## 5. Models Involved

- New `ExecutiveReportRequest` protected request/result/download record.
- New `CriticalTaskAlert` protected retry-safe alert outbox record.
- Existing User, Task, Project, Course, AttendanceSubmission, AttendanceEntry,
  Notification, and AuditEvent models.

## 6. Pages and Endpoints Involved

- No public application page and no general public API.
- Signed start/status/download endpoints under `/integrations/n8n/telegram/`.
- Signed critical-alert claim and acknowledgement endpoints under the same
  prefix.
- An n8n Telegram Trigger workflow with fixed command routing.

## 7. Permission Requirements

- New model permissions are granted only to the CEO role.
- Every integration request resolves the configured username to one active
  CEO and verifies the supplied chat ID against the configured chat ID before
  accessing business data.
- Technical Admin, Executive Manager, Project Manager, Supervisor, Employee,
  Contractor, anonymous callers, other Telegram chats, and inactive CEOs have
  no Phase 16 access.

## 8. Validation Rules

- Report type is `current_tasks`, `overdue_tasks`, or `attendance`.
- Report window is 7, 14, or 30 days; task reports use the current local date
  where a historical window is not applicable.
- Integration JSON bodies are bounded and reject unknown fields.
- Timestamp skew is at most five minutes and every nonce is accepted once.
- Signatures use HMAC-SHA256 over the documented canonical request.
- Downloads expire after ten minutes and succeed once.
- Report evidence and rows are limited to 500 records with explicit
  truncation.
- Alert claims contain at most 20 records and expire after five minutes.

## 9. Business Rules

- Telegram/n8n is read-only with respect to projects, tasks, attendance, and
  every other source business record.
- The CEO explicitly approved sending trainee full names and attendance values
  to the bound CEO Telegram chat on 2026-08-04.
- Trainee names remain local during AI generation. Groq receives aggregate
  attendance counts only; Django adds the named rows deterministically to the
  final PDF.
- A critical task is active, non-archived, has Critical priority, is not
  Completed or Cancelled, and is due today, tomorrow, or overdue.
- One alert is created per task/priority/status/due-date fingerprint. Delivery
  is complete only after n8n acknowledges it.
- n8n must disable successful and failed execution-data retention. Its native
  credential store holds the Telegram token, while the signing secret is
  injected from the deployment secret manager and never exported with the
  workflow.
- Report and alert records are protected from normal hard deletion. The PDF is
  rendered in memory and is not stored as an uploaded file.

## 10. Expected Migrations

- Initial executive-report and critical-alert models, indexes, lifecycle
  constraints, uniqueness, and protected relations.
- Phase 16 CEO-only permission seed.
- Phase 16 audit scope choice.

## 11. Unit Tests

- HMAC canonicalization, signature/timestamp/nonce/chat checks, and replay.
- Evidence selection, exclusions, bounds, named attendance appendix, and
  aggregate-only Groq payload.
- Strict AI schema validation, one-time token validation, PDF building, and
  critical-task fingerprints.

## 12. Integration Tests

- CEO start/queue/complete/status/download lifecycle.
- Wrong chat, wrong role, inactive CEO, bad signature, expired timestamp,
  replayed nonce, unknown command, and second-download denial.
- Arabic named attendance PDF without phone/email/notes and aggregate-only
  provider input.
- Critical alert create/claim/lease expiry/acknowledgement/idempotency.
- Audit metadata excludes personal and secret values.

## 13. Browser and Workflow Tests

- Import/lint the n8n workflow JSON and verify every fixed command branch.
- Exercise the signed API from a test client representing n8n.
- Render the Arabic PDFs and inspect RTL text, brand dimensions, tables,
  multi-page behavior, and mobile Telegram-friendly filenames/messages.

## 14. Security Tests

- Constant-time signature and configured-chat comparison.
- Replay, timing, body-size, method, and direct download-token attacks.
- No names in Groq requests, audit metadata, logs, critical-alert text beyond
  approved task names, URLs, or filenames.
- No bot/signing/Groq secret in source or exported workflow.
- Fail closed when production configuration is incomplete or not HTTPS.

## 15. Manual Verification

- Import the workflow into a dedicated n8n staging project with execution
  retention disabled and fictional Arabic data.
- Bind a staging Telegram bot and CEO chat, run every command, open every PDF,
  confirm one-time download failure, and simulate critical alert retry/ack.
- Inspect n8n, Django, worker, audit, and provider logs for secret/personal-data
  leakage.

## 16. Acceptance Criteria

- Only the exact configured active CEO/chat pair receives results.
- All fixed commands return correct Arabic, permission-scoped, bounded output.
- Attendance PDFs include approved trainee names/statuses while Groq sees only
  aggregates and Telegram receives no other trainee contact/private fields.
- Critical alerts are deduplicated, leased, retried, and acknowledged without
  changing the task.
- Every PDF is branded, RTL-safe, contains Gregorian and Hijri dates, expires
  in ten minutes, and downloads once.
- HMAC/replay/body/configuration tests and the full quality gate pass.

## 17. Dependencies

- Phase 15 Groq provider, Celery/Redis, existing task and attendance selectors,
  report branding/font assets, PostgreSQL, n8n, and Telegram Bot API.
- Deployment-provided CEO username/chat ID, n8n signing secret, public HTTPS
  application origin, n8n base URL, Telegram credential, and Groq key.

## 18. Rollback Considerations

Disable the Phase 16 feature flag, deactivate the n8n workflow, and revoke the
Telegram bot and signing credentials. Preserve request/alert/audit evidence.
The application, Phase 15, reports, tasks, and attendance continue normally.
