# Phase 17: Agentic Project Recovery and Planning

Status: Completed and verified locally on 2026-08-04

## 1. Goal

Provide a permission-scoped Groq project agent that analyzes delays,
blockers, deadlines, approvals, progress, and workload; builds a cited
recovery plan; proposes allowlisted actions; pauses for human approval; and
executes only approved actions through existing domain services before
verifying the final state.

## 2. Included Features

- Predefined project-recovery goals with a small bounded optional-context
  field; Phase 17 is not an unrestricted chatbot.
- A bounded plan/tool/observation/proposal/verification loop with at most
  eight stored steps and configured token, time, daily-request, and result
  limits.
- Dynamically selected allowlisted read tools:
  `get_project_snapshot`, `list_overdue_and_blocked_tasks`,
  `get_upcoming_milestones`, `get_pending_approvals`,
  `get_team_workload`, `calculate_project_progress`, and
  `recall_reviewed_agent_runs`.
- Proposal-only tools: `propose_task_update`, `propose_task_assignment`,
  `propose_task_comment`, `propose_deadline_change`, and
  `propose_team_notification`.
- Human approval or rejection with a required reason and an explicit
  before/after comparison.
- Transactional, idempotent execution through existing business services
  after fresh permission, scope, lifecycle, and before-state checks.
- Reviewed project memory. Only a completed run explicitly reviewed by an
  authorized user may create memory for later runs.
- Cited Arabic or English plans, observations, proposals, and final
  verification reports.
- Celery execution, bounded retry, cancellation, stale-run recovery, and safe
  localized notifications.
- An optional signed n8n reviewed-event workflow and a separate repository
  skill at `skills/insight-project-agent/SKILL.md`.

## 3. Excluded Features

- Changes to the Phase 15 read-only briefing provider, evidence boundary,
  no-tools guarantee, or no-autonomous-write guarantee.
- Shell commands, raw SQL, filesystem access, code execution, web search,
  arbitrary HTTP or URLs, credentials, files, raw audit metadata, budgets,
  trainee data, or attendance data.
- Free-form chat, user-defined tools, provider-selected URLs, arbitrary model
  identifiers, or actions outside the five proposal types.
- Automatic proposal approval, bulk approval, approval delegation, or
  execution under the requester's identity when another user approved.
- Direct task completion, project/course/milestone completion, approval
  decisions, attendance changes, deletion, archive/restore, or bypassing any
  existing completion-approval workflow.
- Sending arbitrary model text as a notification. Team notifications use
  fixed reviewed bilingual application content and a safe internal link.

## 4. User Stories

- As an authorized project user, I can start a recovery analysis for a
  project I can currently access.
- As a reviewer, I can inspect every bounded plan/tool/observation step and
  its citations before trusting the result.
- As an authorized decision maker, I can approve or reject one proposal with
  a reason and see exactly what will change.
- As a project manager, I can execute an approved proposal only while I still
  have the underlying business permission and the source state is unchanged.
- As a reviewer, I can mark a verified run reviewed so its safe cited summary
  can help a later run on the same project.

## 5. Models Involved

- New protected `AgentRun`, `AgentStep`, `AgentToolCall`, `AgentProposal`, and
  `AgentMemory` records.
- New protected reviewed-event records and temporary digest-only integration
  nonces for the optional n8n workflow. Expired nonce security state is
  removed by scheduled maintenance.
- Existing User, Project, ProjectMembership, Task, TaskAssignment,
  TaskComment, Milestone, ApprovalRequest, Notification, and AuditEvent
  records.

## 6. Pages and Endpoints Involved

- "Start Project Agent" on an eligible project detail page.
- A bilingual request form, HTMX-compatible live timeline, cited final
  report, proposal approval queue, before/after comparison, and final
  verification result under `/project-agent/`.
- Signed, bounded reviewed-event claim and callback endpoints under
  `/integrations/n8n/project-agent/`.

## 7. Permission Requirements

- Active CEO, Executive Manager, owning Project Manager, and assigned
  Supervisor may start, view, and review runs only inside current project
  visibility.
- Approval and execution require the Phase 17 approve/execute permission plus
  the approving actor's current underlying domain permission for the exact
  proposed object and action.
- CEO is read-only in existing business domains and therefore cannot execute
  a write proposal. Executive Manager and owning Project Manager can execute
  proposals they could perform directly. A Supervisor can execute only an
  assigned-task update or comment already permitted by the task domain.
- Technical Admin, Employee, Contractor, inactive accounts, anonymous users,
  and users outside current object scope have no Phase 17 access.
- Authorization and object scope are rechecked when requesting a run, before
  every tool read, at approval/rejection, before execution, and during
  verification.

## 8. Validation Rules

- Goal templates, language, model, tool names, action names, arguments, and
  state transitions use stable allowlisted codes and strict schemas.
- The default model is `openai/gpt-oss-120b`; an explicit request may select
  `openai/gpt-oss-20b`. No other model is accepted.
- Optional context is plain text, normalized for storage, limited to 500
  characters, labelled as untrusted, and cannot select tools, objects,
  recipients, permissions, or actions.
- Every factual statement and proposal cites a server-issued source reference
  from a successful tool observation in the same run or a reviewed memory.
- Provider-returned record identifiers are valid only when they were exposed
  by a permitted observation in the same run and remain in current scope.
- Task status proposals are limited to Todo, In Progress, or Blocked.
  Completed, Cancelled, and Pending Approval are rejected.
- Assignment targets must be active eligible project members. Deadline
  changes must satisfy existing task, parent, course, and project date rules.
- Approval/rejection reasons are required and bounded. Duplicate decisions or
  executions are idempotent. An undecided proposal expires after the bounded
  configured TTL (72 hours by default) and cannot later be approved.

## 9. Business Rules

- Phase 17 never performs a write from model output. The model can only ask
  the server to create a pending proposal.
- At least two distinct successful read tools are required before a proposal
  or final plan is accepted. Each next provider request receives only safe
  structured observations, so observations materially influence planning.
- Database strings are untrusted prompt data. Prompts, chain-of-thought,
  secrets, raw provider responses, and raw provider errors are not persisted.
- To avoid a redundant provider round trip, the strict proposal decision also
  carries the cited recovery findings and recommendations used to create the
  stored final-report step. Token accounting still includes every provider
  input/output token and fails closed at the run budget.
- The approving user is the execution actor. Current permission and object
  scope cannot be inherited from the requester or from a previous step.
- Execution locks the proposal and target, validates the stored before-state
  fingerprint, calls the existing domain service, records an idempotency key,
  and verifies the after-state. A mismatch produces `stale` and no write.
- Team notification execution sends fixed bilingual content only to active
  current project members who can access the project. Provider text is not
  copied into the delivered notification.
- Runs and proposals are protected records governed by the approved Phase 14
  retention policy. Only explicitly reviewed completed runs enter memory.

## 10. Expected Migrations

- Initial Phase 17 protected models, state constraints, indexes, uniqueness,
  and protected relations.
- Phase 17 role-permission seed.
- New project-agent audit scope and fixed notification category/content.

## 11. Unit Tests

- Strict schemas, stable codes, citations, fingerprints, token/step/result
  limits, prompt-injection handling, and safe provider failures.
- Dynamic multi-tool planning where an observation changes the next tool.
- Every read tool's scope, exclusions, bounds, and deterministic references.
- Reviewed-memory creation and later recall; unreviewed or out-of-scope memory
  rejection.
- Proposal validation, unsupported actions, forged IDs, stale fingerprints,
  and idempotent execution.
- n8n HMAC, timestamp, nonce, replay, schema, and callback validation.

## 12. Integration Tests

- Queue, plan, two-tool observation loop, proposal, awaiting-approval,
  approve/reject, execute, verify, complete, cancel, expire, and fail flows.
- Unauthorized start/read/tool/approval/execution, revoked access mid-run,
  provider timeout/retry, quota and token-budget exhaustion.
- Existing task update, assignment, comment, deadline, and fixed notification
  services are reused without bypassing completion approval.
- Duplicate execution returns the first verified result without a second
  write or notification.

## 13. Browser and Workflow Tests

- Arabic RTL and English LTR request, live timeline, citations, proposals,
  decisions, before/after, memory review, and verification.
- Mobile layouts keep controls, long Arabic text, tables, citations, and
  direction-isolated codes usable at representative narrow widths.
- Import/lint the inactive n8n workflow and exercise signed claim, replay,
  human-checkpoint callback, safe notification/archive, and failure paths.

## 14. Security Tests

- Prompt injection inside project/task names, optional context, and comments
  cannot add tools, change schemas, forge IDs, reveal hidden data, or bypass
  approval.
- Shell, raw SQL, filesystem, arbitrary URL, web, code, credential, file,
  trainee, attendance, raw-audit, and unrestricted-tool requests fail closed.
- Object access revoked between request/tool/approval/execution/verification
  fails without disclosure or partial write.
- Concurrency, stale state, duplicate execution, expired proposals, oversized
  results, malformed provider output, and over-budget calls fail safely.
- Audit/log/notification records contain stable codes and bounded summaries,
  never prompts, chain-of-thought, secrets, provider payloads, or raw errors.

## 15. Manual Verification

- Use fictional Arabic and English project data to run recovery plans with
  overdue work, blockers, deadlines, pending approvals, and uneven workload.
- Confirm the timeline demonstrates a goal plan, two dynamic tools,
  observation-dependent selection, a pending proposal, human approval,
  transactional execution, and a cited verification result.
- Review one run, start another, and confirm reviewed memory is cited while an
  unreviewed run is absent.
- Change a proposed target before execution and confirm the proposal becomes
  stale without changing the target.
- Import the n8n workflow into staging with secret-managed credentials and
  disabled execution-data retention; exercise approval and failure paths.

## 16. Acceptance Criteria

1. A predefined goal produces a bounded, stored multi-step plan.
2. A successful run dynamically selects at least two distinct read tools.
3. A stored observation materially affects the next selected step.
4. Only reviewed memory is used and cited by a later run on the same project.
5. Every write-capable intention becomes a pending proposal and pauses for a
   human decision.
6. An approved proposal executes exactly once only after current permission,
   scope, lifecycle, and before-state checks.
7. The run ends with a cited verification summary of the actual final state.
8. Arabic RTL/mobile and English LTR flows are complete and tested.
9. Malicious, unauthorized, forged-ID, stale, over-budget, prompt-injection,
   replay, and duplicate attempts fail safely and are audited.

## 17. Dependencies

- Phase 15 Groq transport conventions without sharing its no-tools runtime.
- Existing project/task/approval/progress/notification/audit services,
  PostgreSQL, Celery/Redis, HTMX, Bootstrap, n8n, and deployment secret
  management.
- `GROQ_API_KEY` and an explicit Phase 17 feature/provider configuration.

## 18. Rollback Considerations

Disable the Phase 17 feature flag, stop its Celery queue/maintenance task, and
deactivate the optional n8n workflow. Pending proposals remain non-executable,
and all run/proposal/memory/audit evidence is retained. Phase 15, Phase 16,
and every existing domain continue independently.
