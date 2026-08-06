# Workflows

## Account Lifecycle

1. An authorized administrator creates the account.
2. The administrator assigns one department and one approved predefined role.
3. The user signs in with a temporary hashed password and must replace it.
4. The user may change their password and persisted language preference.
5. Technical Admin may update non-security profile fields, reset a password,
   or deactivate/reactivate the account.
6. Deactivation revokes all sessions; reactivation requires a new login.
7. Lifecycle and role changes create append-only audit records.

Only a superuser may grant or revoke Technical Admin. Accounts are never
hard-deleted.

## Project and Course Lifecycle

Phase 3 project lifecycle:

1. Executive Manager or Project Manager creates a Draft project in an owning
   department with a required eligible manager.
2. The creator may assign an eligible supervisor and active department team
   members.
3. Executive Manager may manage any project. Project Manager may manage only
   a project for which they are the manager.
4. Draft may become Active or Cancelled; Active may become On Hold or
   Cancelled; On Hold may become Active or Cancelled; Cancelled may return to
   Draft.
5. Authorized actors archive instead of deleting. Archived projects are
   read-only until restored.
6. Project, status, team, archive, client, and category changes are audited.

Phase 4 course lifecycle:

1. Executive Manager or the owning Project Manager creates a Draft course
   inside a non-archived permitted project.
2. Draft may become Active or Cancelled; Active may become On Hold or
   Cancelled; On Hold may become Active or Cancelled; Cancelled may return to
   Draft.
3. A course may be Active only while its project is Active.
4. Authorized actors assign active external trainers and upload approved
   private files.
5. Course archive makes the course read-only and end-dates active trainer
   assignments. Restore does not reactivate prior assignments.
6. Course, trainer, assignment, file, status, archive, and restore actions are
   audited.

Project and course completion use the Phase 7 approval workflow below.

## Task Lifecycle

Phase 5 task lifecycle:

1. Executive Manager or the owning Project Manager creates a To Do task under
   exactly one non-archived project or course.
2. A task has one or more eligible assignees, exactly one active primary
   owner, and up to three acyclic same-owner hierarchy levels.
3. To Do may become In Progress or Cancelled; In Progress may become Blocked,
   Completed, or Cancelled; Blocked may become In Progress or Cancelled;
   Completed may return to In Progress; Cancelled may return to To Do.
4. Blocked requires a reason. An assignee may update only status, actual
   hours, and blocking reason.
5. Authorized collaborators add immutable comments and approved private
   files. Managers select and administer bilingual tags.
6. Archive makes a task read-only, end-dates active assignments and tag links,
   and requires subtasks to be archived first. Restore recreates the latest
   still-eligible assignment set without rewriting history.
7. Task, assignment, status, comment, file, tag, archive, and restore actions
   create append-only task-scope audit events.

Dependencies, recurrence, task approvals, watchers, and notifications remain
deferred.

## Progress Calculation

Phase 6 progress is calculated on demand through one service:

1. Completed leaf tasks are 100 percent; other countable leaf statuses are
   0 percent.
2. Cancelled/archived task branches are excluded.
3. Parent tasks average direct countable children recursively.
4. Courses average top-level course tasks.
5. Projects equally average available direct-task and course categories.
6. Empty and excluded states are explicit; public values are Decimal-safe,
   bounded, and rounded half-up to two decimal places.

Milestones, approvals, attendance components, dashboards, and reports extend
the same service only in their approved later phases.

## Milestone and Completion Approval

1. Executive Manager or the owning Project Manager maintains milestones.
2. An eligible task, course, milestone, or project completion is submitted.
3. The project Supervisor decides first.
4. Approval advances the request to the Project Manager; rejection requires a
   reason and returns the target to active work.
5. Project Manager approval completes the request and its target.
6. A rejected target may be resubmitted as a new attempt; prior attempts and
   decisions remain immutable.
7. Pending targets cannot be normally edited or archived. Phase 7 has no
   override.

## Trainee Import

1. An authorized user uploads a CSV or Excel file.
2. The system validates format and content without committing data.
3. The user reviews a preview containing valid rows, warnings, duplicates,
   and errors.
4. Existing-course duplicates are explicitly skipped or updated. A duplicate
   repeated inside the same file can only be skipped.
5. Errors block confirmation. The system locks the course, rechecks duplicate
   and capacity state, and writes every valid resolution atomically.
6. The system allocates new course-specific trainee numbers in original file
   order and records an audit entry.
7. Cancellation retains protected preview evidence but writes no trainees.

## Trainer Attendance

1. An authorized user creates a scheduled session.
2. The system generates a random, expiring trainer link.
3. The external trainer opens the link and submits attendance.
   The link is token-bound to one session, expiry is rechecked on submit, and
   every locked trainee requires Present, Absent, Late, or Excused.
4. The submission enters supervisor review.
5. The supervisor approves or rejects it.
6. Rejection requires a reason, reopens the same link, and assigns a new
   expiration.
7. Approved attendance is read-only through the trainer link.
8. An authorized internal correction requires a reason and audit entry and
   does not restart approval.

## Notifications

Task assignment, approval, deadline/overdue, and mention events create
permission-safe in-app notifications. Approval alerts are mandatory in-app;
users configure the other in-app channels and all email channels. Email is
queued after the domain transaction commits.

At 08:00 Asia/Riyadh, scheduled work creates one active-assignee reminder for
tasks due tomorrow and one reminder for each overdue day. Completed,
cancelled, archived, and cancelled-owner-context tasks are excluded. Stable
recipient/event keys deduplicate notification creation, and bounded Celery
jobs record retry-safe delivery state. Phase 11 has no escalation chain.

## Archive and Recovery

Authorized users archive important records. Restoration means restoring an
archived application record, not restoring a database backup. Database backup
restoration is handled through a documented operational procedure.

## AI Project Briefing

1. An authorized user selects a visible, non-archived project, Arabic or
   English, a 7/14/30-day evidence window, and executive or operational detail.
2. The system applies the daily quota, creates a queued request, records an
   audit event, and schedules background generation after commit.
3. The worker rechecks the requester's active account, permission, and current
   project visibility before collecting allowlisted project evidence.
4. The system sends only the approved evidence JSON to Groq. The request uses
   strict JSON Schema mode and provides no tools, browsing, or actions.
5. The system validates structure and citations against the evidence allowlist
   before saving a completed briefing and its source references.
6. Invalid or temporarily unavailable responses retry within bounded limits;
   terminal failure stores only a safe error code.
7. The requester receives an in-app completion notification. Any currently
   authorized briefing user may read the draft and follow its internal source
   links; an authorized reviewer may mark it reviewed.
8. AI output never mutates projects, tasks, approvals, attendance, or any other
   business record.

## CEO Telegram and n8n Executive Reports

1. The CEO sends `/tasks`, `/overdue`, `/attendance`, or `/help` to the
   dedicated Telegram bot in the configured private chat.
2. n8n rejects every other chat and maps the fixed command to a bounded request.
3. n8n signs the canonical HTTPS request with a timestamp and unique nonce.
4. Django verifies feature/configuration state, HMAC, freshness, nonce replay,
   exact chat binding, active configured CEO identity, and CEO permission.
5. For a report, Django queues an idempotent Celery job and returns an opaque
   request identifier. n8n polls the signed status endpoint.
6. Django gathers permission-scoped source data. Groq receives only compact
   aggregate evidence and returns a strict Arabic executive summary. Named
   attendance rows remain local and are added deterministically to the PDF.
7. When complete, n8n obtains a ten-minute one-time download URL, downloads
   the in-memory branded Arabic PDF, and sends it as a Telegram document.
8. A scheduled n8n branch asks Django to claim qualifying critical alerts.
   Django leases pending outbox rows; n8n sends the Arabic messages and then
   acknowledges the lease. Expired unacknowledged leases are retried.
9. Django audits safe lifecycle codes and counts only. No business source is
   changed and no name, chat ID, token, report content, or secret is audited.

## Agentic Project Recovery and Planning

1. An authorized user selects a visible non-archived project, a predefined
   recovery goal, Arabic or English, the approved Groq model, and optional
   bounded context.
2. The system applies the daily and run budgets, creates a queued run, records
   a safe audit event, and schedules the agent loop after commit.
3. The worker rechecks the requester and project, stores a strict plan, then
   asks for one allowlisted read tool at a time. Each tool rechecks current
   permission and scope and returns bounded, cited structured observations.
4. At least two distinct successful read tools are required. A stored
   observation is supplied to the next planning turn and must affect the next
   step. Only explicitly reviewed same-project memory is recallable.
5. A write-capable intention creates a pending proposal with server-validated
   arguments, citations, risk, and a before-state fingerprint. The run enters
   `awaiting_approval`; no business record changes.
6. An authorized user approves or rejects one proposal with a reason. Rejected
   proposals never execute. Approval does not preserve old authority.
7. Celery locks an approved proposal and its target, rechecks the approver's
   current Phase 17 and domain permissions, object scope, lifecycle, and
   before-state fingerprint, then calls the existing domain service exactly
   once using its idempotency key.
8. The worker reads the actual result under current scope and stores a cited
   verification step. Stale or revoked state fails closed without a partial
   write. A completed verified run may be explicitly reviewed into project
   memory.
9. The optional n8n branch claims a safe reviewed-event envelope through a
   signed, replay-protected endpoint, pauses at its own human checkpoint, then
   sends a signed idempotent callback for safe notification/archive handling.

## Telegram AI Executive Assistant

1. The configured CEO sends a standalone Arabic or English non-command text
   message to the dedicated private bot.
2. n8n rejects every other chat, rejects unknown slash commands, detects the
   response language, and sends a signed bounded start request containing the
   Telegram message ID and question.
3. Django rechecks configuration, HMAC, freshness, nonce, exact CEO/chat,
   assistant permission, idempotency, quota, length, supported topic, and
   unsafe-content patterns before creating a queued protected request.
4. Celery rechecks current authority and gathers a small deterministic ranking
   of currently visible project, task, milestone, and approval evidence.
5. Groq receives the standalone question and untrusted structured evidence,
   has no tools, and returns strict cited JSON in the requested language.
6. Django validates every citation, resolves safe labels, formats a Telegram-
   length answer, and stores no provider prompt, envelope, or raw error.
7. n8n polls the signed status endpoint and sends only the completed safe text
   to the same configured chat. Each status read rechecks current authority.
8. Unsupported, malicious, personal-data, secret, or write requests return a
   fixed safe response without a provider call. No conversation memory exists.

## Workflow Approval

Status: Account lifecycle and Phase 3 through Phase 17 domain lifecycles and
the Phase 19 read-only Telegram assistant are approved. Other phase-specific
transitions and permissions require later approval.
