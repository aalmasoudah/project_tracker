# Phase 15: AI Project Briefings

Status: Completed and verified on 2026-08-04

## 1. Goal

Generate useful Arabic or English project briefings from permission-scoped
application evidence while keeping every result cited, reviewable, read-only,
and independent from core project workflows.

## 2. Included Features

- Project-level AI briefing requests.
- Arabic or English output.
- Executive or operational detail.
- 7, 14, or 30-day evidence windows.
- Asynchronous Celery generation with HTMX status polling.
- Groq Chat Completions using strict JSON Schema.
- `openai/gpt-oss-120b` default and approved `openai/gpt-oss-20b` override.
- Summary, highlights, risks, upcoming items, recommended actions, and data
  gaps.
- Internal source citations, truncation disclosure, review state, audit events,
  and completion notification.
- Deterministic fake provider for local automated tests.

## 3. Excluded Features

- General chat, custom prompts, cross-project portfolio briefings, external web
  search, provider tools, code execution, and autonomous writes.
- Budgets, task comments, uploaded files or contents, attendance, trainees,
  credentials, raw audit metadata, and environment configuration.
- Editing or deleting completed briefings through normal application paths.

## 4. User Stories

- As an authorized leader, I can request a concise cited project briefing.
- As an Arabic user, I receive a complete RTL Arabic briefing.
- As a reviewer, I can inspect every factual item and mark the draft reviewed.
- As an unauthorized user, I cannot discover a project or its briefing.
- As an operator, I can enable Groq without putting its API key in source code.

## 5. Models Involved

- New `AIBriefing` request/result/review record.
- New `AIBriefingSource` allowlisted evidence reference.
- Existing Project, Task, Course, Milestone, ApprovalRequest, User,
  Notification, and AuditEvent models.

## 6. Pages Involved

- Project detail Generate AI Briefing action.
- Briefing request form.
- Briefing status/result detail and HTMX status fragment.
- Mark-reviewed POST action.

## 7. Permission Requirements

- `generate_aibriefing`, `view_aibriefing`, and `review_aibriefing` are granted
  only to CEO, Executive Manager, Project Manager, and Supervisor.
- Existing project visibility narrows every permission.
- Project Managers are limited to managed projects; Supervisors are limited to
  active supervised projects.
- Technical Admin, Employee, and Contractor have no Phase 15 access.

## 8. Validation Rules

- Language is `ar` or `en`; detail is `executive` or `operational`; evidence
  window is 7, 14, or 30 days.
- Each user may request at most 20 briefings per local day.
- Evidence includes at most 200 detailed source records and reports truncation.
- Provider output must match the strict JSON Schema and every factual list item
  must cite one or more evidence references present in the request allowlist.
- Provider, endpoint, model, and secret configuration fail closed.

## 9. Business Rules

- Briefings are non-authoritative AI-generated drafts and never update business
  records.
- Permission is checked when requested, generated, viewed, and reviewed.
- Prompt data is untrusted; output is escaped by Django templates.
- A failed generation stores only bounded safe codes, never provider secrets,
  prompt contents, or raw error responses.
- Briefings and source references are retained indefinitely and protected from
  normal deletion.

## 10. Expected Migrations

- Initial `ai_briefings` models, constraints, indexes, and permissions.
- Phase 15 role-permission seed.
- Audit AI scope choice.
- Notification AI briefing category choice and constraints.

## 11. Unit Tests

- Evidence selection, exclusions, ordering, limits, and truncation.
- Strict schema and citation validation.
- Fake and Groq provider configuration/response handling.
- Permission policies and quota boundaries.

## 12. Integration Tests

- Queued-to-completed and safe failure lifecycles.
- Current object-level authorization on request/read/review/generation.
- Arabic and English output, audit events, notification, citations, and review.
- Archived projects, revoked access, prompt injection text, exclusion fields,
  and quota enforcement.

## 13. Browser Tests

- Arabic RTL request, status/result, source navigation, and review workflow.
- Representative English LTR request and result.
- Responsive project-detail action and briefing output.

## 14. Security Tests

- Cross-project ID enumeration returns 404.
- Provider payload excludes unapproved fields and secrets.
- Unsupported citations and malformed schemas are rejected.
- Database prompt-injection text remains inert data.
- Groq is disabled without explicit safe configuration.

## 15. Manual Verification

- Run a worker and Redis, enable Groq, request both languages and both detail
  modes, inspect citations, review state, notifications, and audit entries.
- Verify mobile layouts, RTL mirroring, long Arabic text, mixed-direction model
  IDs, failure messaging, and disabled-feature behavior.

## 16. Acceptance Criteria

- An authorized user can request a cited project briefing and receive it
  asynchronously without affecting normal project work.
- The result contains all approved sections in the selected language and each
  factual item links only to evidence the current user may access.
- Unauthorized and no-longer-authorized users cannot discover briefings.
- Groq uses strict schema mode with an approved model and no tools.
- Every lifecycle action is safely audited; completion creates an idempotent
  notification; review is explicit and attributable.
- Arabic/English UI and critical browser workflows pass.

## 17. Dependencies

- Existing project visibility, progress service, tasks, milestones, approvals,
  audit, notifications, Celery, Redis, and PostgreSQL.
- A deployment-provided `GROQ_API_KEY` for live generation.

## 18. Rollback Considerations

Disable the feature flag and stop accepting new requests. Preserve existing
briefing and evidence records under the retention rule. The core application
continues without Groq because provider failures never alter domain records.
