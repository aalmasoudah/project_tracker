# Business Rules

This file contains rules that affect calculations, approvals, permissions,
and record integrity. The development playbook intentionally does not define
all company-specific behavior, so unresolved rules are listed explicitly and
must be approved before their implementation phase.

## Confirmed Rules

- PostgreSQL is the system of record in all environments.
- Important business records are archived instead of normally deleted.
- Phase 5 task nesting is limited to three levels with acyclic, same-owner
  parent chains.
- Attendance submission always requires supervisor approval.
- Rejecting attendance requires a reason and reopens the same trainer link
  with a new expiration.
- Approved attendance is read-only through the trainer link.
- An authorized correction to approved attendance requires a reason and an
  audit entry, but does not require reapproval.
- Background jobs must be idempotent and safe to retry.
- Reports must use the same centralized progress calculations as dashboards.
- Uploaded files must be checked for size, extension, and MIME type.
- Secure external links must be random and expiring; token hashes should be
  stored where practical.
- Arabic and English are first-class supported languages. User-facing pages,
  validation, notifications, operational views, and reports must support the
  active language and correct RTL/LTR direction.
- Accounts, departments, and Phase 2 audit records are never hard-deleted
  through the application. Expired login-throttle counters are temporary
  security data and may be deleted.
- Arabic is the default application language, and each internal user may
  persist an Arabic or English preference.
- The project owner approves official Arabic business terminology. Phase 2
  role terminology is approved in decision 0007.
- Account identity preserves original Arabic text. Username and email identity
  comparisons are case-insensitive, while Arabic letter folding is limited to
  derived search behavior and never changes stored text.
- Phase 3 project statuses are Draft, Active, On Hold, and Cancelled with the
  transitions recorded in decision 0008. Project completion remains deferred
  to Phase 7.
- Phase 3 project dates are required Gregorian date-only values using Western
  digits; the end date cannot precede the start date.
- Phase 3 budgets are optional, non-negative SAR amounts with at most two
  decimal places. Extra precision is rejected.
- Projects, clients, categories, and memberships are archived or end-dated
  instead of hard-deleted through the application.
- Phase 4 course statuses are Draft, Active, On Hold, and Cancelled with the
  transitions recorded in decision 0009. Course completion remains deferred
  to Phase 7.
- Phase 4 course schedules use timezone-aware datetimes entered and displayed
  in Asia/Riyadh with Gregorian dates and Western digits.
- Courses and trainers are archived rather than hard-deleted; trainer
  assignments are end-dated.
- Phase 5 task statuses are To Do, In Progress, Blocked, Completed, and
  Cancelled. Approved transitions are recorded in decision 0010; Blocked
  requires a reason.
- Every task belongs to exactly one project or course, has one active primary
  owner among one or more eligible assignees, and keeps an immutable code and
  owner context.
- Task dates are optional Gregorian date-only values using Western digits,
  must be ordered, and must stay within the owning project/course schedule.
  Task overdue semantics remain deferred.
- Estimated and actual task hours are optional non-negative values with at
  most two decimal places; actual may exceed estimated and neither affects
  progress in Phase 5.
- Tasks and tags are archived, comments/files are immutable, and assignments
  and task-tag links are end-dated instead of hard-deleted.
- Phase 6 leaf-task progress is status-based: Completed is 100 percent and
  To Do, In Progress, and Blocked are 0 percent. Cancelled/archived task
  branches are excluded.
- A parent task recursively averages its direct countable children. With no
  countable children, its own leaf status applies.
- Course progress averages top-level course tasks. Project progress equally
  averages the direct-project-task and course categories that exist; records
  inside each category have equal weight.
- Empty countable collections produce 0 percent with an explicit empty state.
  Cancelled/archived courses and projects are not applicable.
- Progress uses unrounded `Decimal` calculations and public two-decimal
  `ROUND_HALF_UP` results bounded from 0 through 100. Task hours do not affect
  progress.
- Phase 7 completion approval is sequential: the owning project Supervisor,
  then Project Manager. Rejection requires a reason and resubmission creates a
  new immutable attempt.
- Completed milestones are 100 percent; other countable milestone statuses
  are 0 percent. Cancelled/archived milestones are excluded, and milestones
  form an equal available category in project progress.
- Tasks, courses, and projects require 100-percent progress before completion
  submission. Milestones may submit from In Progress because approval changes
  them to Completed.
- Approved course and project completion adds a Completed status reachable
  only through the approval service. Phase 7 provides no override.
- Phase 8 trainee identity requires full name and phone. A duplicate exists
  only when their approved derived keys repeat in the same course.
- Enrollment numbers are positive, course-specific, allocated in source order,
  immutable, and never reused. Active enrollments cannot exceed capacity.
- Phase 8 imports are previewed without trainee writes. Errors block
  confirmation; duplicates use explicit Skip/Update resolution; confirmation
  is atomic and audited.
- Phase 9 attendance values are Present, Absent, Late, and Excused. Session
  submissions require every locked roster row and enter pending review.
- Trainer tokens contain 256 random bits, are stored only as SHA-256 hashes,
  expire at submission time, and are limited to one session.
- Phase 10 attendance is reviewed only by the active owning project's assigned
  Supervisor. Rejection preserves a decision snapshot and reopens the same
  hash-only token for 72 hours.
- Executive Managers may correct any approved attendance and the owning
  Project Manager may correct managed-course attendance. Corrections require
  a reason and immutable before/after evidence, remain approved, and do not
  return to review.
- Phase 11 notification categories are task assignment, approval,
  deadline/overdue, and mention. Approval is mandatory in-app; users may
  configure the other in-app channels and every email channel.
- Task reminders run at 08:00 Asia/Riyadh on the day before the due date and
  daily while overdue. Only active assignees receive them; completed,
  cancelled, archived, and cancelled-owner-context tasks are excluded.
- Notification content is fixed, generic, bilingual, and permission-safe.
  Notification, preference, and delivery records are protected from normal
  hard deletion. Celery email jobs are bounded, deduplicated, and retry-safe.
- Phase 14 retains application business records, uploaded files,
  notifications, delivery evidence, audit records, and archived data
  indefinitely for the initial release. It provides no automated purge or
  hard-delete path.
- Phase 14 administrative export is limited to sanitized, permission-scoped
  audit CSV. Personal-data, individual-attendance, uploaded-file, and raw
  metadata exports remain excluded.
- Database backup and restoration remain infrastructure operations. Initial
  recovery targets are a 24-hour RPO, an 8-hour RTO, 35-day encrypted backup
  retention, and quarterly isolated restoration testing.
- Phase 15 AI briefings are read-only derived drafts. They cannot create,
  change, approve, archive, notify on behalf of a user, or otherwise mutate
  projects, tasks, progress, milestones, approvals, attendance, or reports.
- AI evidence is assembled by permission-scoped application selectors before
  any provider call. Worker execution and later viewing recheck the requesting
  user's active account and project access.
- Phase 15 evidence excludes budgets, task comments, uploaded-file contents,
  trainee and attendance data, credentials, tokens, raw audit metadata, and
  environment configuration.
- AI output uses a strict validated schema. Every factual risk, highlight,
  upcoming item, and recommended action requires an allowlisted source
  citation; unsupported or unauthorized citations fail validation.
- Database text is untrusted prompt data. The Phase 15 provider receives no
  tools or action capability, and generated content is escaped before HTML
  presentation.
- AI briefing records and their safe source references are protected from
  normal hard deletion and follow the approved indefinite initial-release
  application retention rule.
- Phase 15 is disabled by default. A real provider call requires an explicit
  feature flag, provider code, HTTPS endpoint, model, and secret supplied by
  environment configuration. The deterministic fake provider is limited to
  development and automated testing.
- Pilot limits are 7, 14, or 30 days of evidence, at most 200 detailed source
  records, and 100 requests per user per local day. Truncation is disclosed in
  the generated briefing.
- Phase 16 Telegram reporting is available only to one deployment-configured
  active CEO username and one exact Telegram chat ID through the approved n8n
  workflow. It is read-only and exposes no general API or free-form prompt.
- Phase 16 integration calls use HMAC-SHA256, a five-minute timestamp window,
  one-use nonces, bounded bodies, and constant-time secret/chat comparison.
- The CEO explicitly approved trainee full names and attendance values in the
  attendance PDF sent to the bound CEO Telegram chat. Phone numbers, emails,
  notes, files, tokens, and other personal fields remain excluded.
- Groq receives only bounded aggregate attendance evidence. Trainee names and
  individual attendance rows are appended locally by Django and never enter
  the AI prompt or provider payload.
- Phase 16 PDFs are rendered in memory, use Arabic RTL with Gregorian and
  Umm al-Qura Hijri dates, expire after ten minutes, and download once.
- Critical Telegram alerts cover active, non-archived, incomplete Critical
  tasks due tomorrow or earlier. A task/status/due-date fingerprint prevents
  duplicates; n8n delivery requires lease acknowledgement and is retry-safe.
- n8n successful execution-data retention is disabled. Telegram, n8n, Django,
  and Groq credentials remain environment/credential-store secrets and never
  appear in source, audit metadata, report content, or logs.
- Phase 17 is a separate permission-scoped agent domain. It does not change
  the Phase 15 no-tools/no-writes boundary and has no access to trainee,
  attendance, file, budget, credential, raw-audit, filesystem, SQL, shell,
  web, code-execution, or arbitrary-HTTP data or capabilities.
- A Phase 17 model may select only approved read or proposal tool codes. It
  never calls a domain write service. At least two distinct successful read
  tools and cited observations are required before a proposal or final plan.
- Only completed verified runs explicitly reviewed by an authorized user
  become same-project memory. Unreviewed or cross-project runs are excluded.
- Every proposal pauses for a human decision. The approver is the execution
  actor and must still hold both Phase 17 and underlying domain authority at
  execution. CEO remains unable to write because existing CEO business
  permissions are read-only.
- Approved execution locks the proposal and target, compares a server-issued
  before-state fingerprint, calls an existing domain service transactionally,
  applies one idempotency key, and reads the actual final state for cited
  verification. Stale, revoked, duplicate, or invalid state writes nothing.
- Phase 17 task-status proposals are limited to Todo, In Progress, or Blocked.
  Completion, cancellation, pending approval, and approval decisions are not
  agent-executable. Team notifications use fixed bilingual content rather
  than arbitrary provider text.
- Phase 17 stores bounded structured plans, calls, observations, proposals,
  and results, but never chain-of-thought, full prompts, provider payloads,
  credentials, secrets, or raw provider errors. Protected records follow the
  approved initial-release retention rule.
- Phase 19 preserves Phase 16 fixed commands and adds only bounded standalone
  Arabic/English executive questions from the exact configured CEO/chat pair.
- Phase 19 questions are read-only, have no tools or memory, and may use only
  permission-scoped project, task, milestone, approval, and aggregate workload
  evidence. Budgets, people, attendance, trainees, comments, files, secrets,
  environment data, and raw audit metadata are excluded.
- Questions are locally bounded and rejected before Groq when they request
  unsupported, personal, secret, prompt/system, URL, shell, SQL, web, or write
  behavior. Every factual answer item requires an allowlisted citation.
- One hashed Telegram message key creates at most one protected assistant
  request. Processing is asynchronous, quota/token/evidence bounded, retry-
  safe, audited without question/answer content, and rechecks authority at
  request, processing, and status retrieval.
- Phase 20 navigation presentation never grants authority; existing view and
  object permissions remain authoritative at every destination.
- Phase 20 progress indicators present only the canonical Phase 6 result and
  introduce no new calculation or portfolio aggregation.
- A user may upload, replace, or deactivate their own verified profile avatar.
  Historical avatar records and stored derivatives remain protected under the
  approved retention rule even after they are no longer displayed.
- Phase 21 LM Studio inference is disabled by default, local-development only,
  and fixed to `http://127.0.0.1:1234/v1`. It cannot be exposed to the LAN,
  phone, n8n, Telegram, a tunnel, staging, or production under this approval.
- Approved local logical model codes are `qwen/qwen3.5-9b` and
  `openai/gpt-oss-20b`. Exactly one operator-pinned API model ID must match its
  loaded ID reported by `/v1/models` and pass the capability gate; installed
  models are never discovered, downloaded, aliased deceptively, or selected
  silently.
- `qwen/qwen3.5-9b` requires `LM_STUDIO_REASONING_EFFORT=none`, proven by the
  live Arabic/English strict-schema probe. A conflicting value fails closed;
  gpt-oss remains unavailable until explicitly installed and independently
  gated.
- A local response is accepted only after strict JSON Schema generation and
  authoritative Django schema, citation, identifier, permission, and scope
  validation. LM Studio has no direct database or business-service access, and
  model reasoning fields are discarded rather than stored or displayed.
- With the global fallback switch explicitly enabled, Phase 16/19 Telegram AI
  and Phase 17 Recovery may transition once from Groq to LM Studio only after
  a locally classified transient provider failure. After one valid local
  decision the request/run stays pinned locally and never oscillates.
- Authentication, configuration, permission, security, unsafe-input, schema,
  citation, quota/budget, cancellation, stale-state, duplicate, and business-
  rule failures never trigger fallback. Local unavailability uses the existing
  bounded safe-failure path. Production remains Groq-only pending a separate
  deployment decision.

## Decisions Required Before Planning

The project owner must approve answers to these questions:

1. [Approved for Phase 5] Maximum task nesting depth is three levels.
2. [Approved for Phase 5] Task statuses and transitions are defined in
   decision 0010. Progress interpretation remains deferred to Phase 6.
3. [Approved for Phase 6] Cancelled and archived task branches are excluded
   from progress denominators.
4. [Approved for Phase 6] Task progress is status-based and recursively
   averaged as defined in decision 0011.
5. [Approved for Phase 6] Course progress averages top-level course tasks.
6. [Approved for Phase 6 projects] Project progress uses equal available
   categories as defined in decision 0011. Milestone progress remains
   deferred to Phase 7.
7. [Approved for Phase 6] Progress is bounded from 0 through 100 percent.
8. [Approved for Phase 3 projects and Phase 4 courses] What are the project
   and course status transitions?
9. [Approved for Phase 7] Completion approval requires Supervisor then Project
   Manager as defined in decision 0012.
10. [Approved through Phase 10] Phase 7 completion approvers and Phase 10
    attendance reviewers/correctors are defined in decisions 0012 and 0015.
11. [Approved for Phase 8] A duplicate is normalized full name plus phone
    inside the same course, as defined in decision 0013.
12. [Approved for Phase 9] Present, Absent, Late, and Excused.
13. [Approved for Phase 9] Expiry is rechecked at submission and commits
    nothing; an authorized actor must issue a new link.
14. [Approved through Phase 11] Project/task date fields, Riyadh course
    schedules, and task reminder/overdue timing are defined in decisions 0008,
    0009, 0010, and 0016.
15. [Approved for Phase 3 project budgets] Which currencies are supported,
    and how are monetary values rounded? Later monetary outputs remain open.
16. [Approved through Phase 14] Accounts, departments, audit events, projects,
    clients, categories, courses, trainers, tasks, tags, comments, and files
    are not hard-deleted; memberships and assignment/tag relationships are
    end-dated. Trainees, enrollments, import batches/rows, and approval history
    are also protected. Attendance sessions, locked rosters, links,
    submissions, entries, evidence, reviews, corrections, notifications,
    preferences, and delivery attempts are protected. Expired throttle
    counters may be deleted. Phase 14 operation evidence is protected and no
    new hard-delete exception is approved.
17. [Approved for Phase 11] Optional category channels and mandatory approval
    in-app behavior are defined in decision 0016.
18. [Approved for Phase 14] Files, audit records, and archived application
    data are retained indefinitely for the initial release. Encrypted
    infrastructure backups are retained for 35 days.
19. [Approved] Arabic is the default language, and each internal user may
    persist Arabic or English.
20. [Approved] The project owner approves official Arabic terminology.
21. [Approved for Phase 3 through Phase 10 screens] Should Arabic display use
    Gregorian or Hijri dates and Arabic-Indic or Western digits in each output
    type? Later outputs remain open.
22. [Approved through Phase 8 search/identity slices] Preserve account
    identity text; apply NFKC to
    usernames and case-insensitive username/email comparison. Derived account
    search may ignore diacritics/tatweel and normalize Alef and Persian
    keyboard variants without merging `ة/ه` or `ى/ي`. Later duplicate policies
    remain open. Phase 8 trainee duplicate normalization is defined in decision
    0013.
23. [Approved for Phase 15] AI project briefings are read-only, permission-
    scoped, cited drafts. Groq is the only approved live provider, using
    `openai/gpt-oss-120b` by default or `openai/gpt-oss-20b` as an explicit
    lower-cost override. The feature has no tools, browsing, or write access.
24. [Approved for Phase 16] The fixed CEO Telegram/n8n workflow, named
    attendance PDF, signed integration boundary, one-time downloads, and
    retry-safe critical alert rules are defined in decision 0021.
25. [Approved for Phase 17] The allowlisted project-recovery agent, reviewed
    memory, human proposal approval, current-authority execution, stale-state
    checks, idempotency, verification, and optional signed n8n reviewed-event
    flow are defined in decision 0022.
26. [Approved for Phase 19] The bounded, cited, read-only CEO Telegram AI
    assistant is defined in decision 0024.
27. [Approved for Phase 20] Permission-preserving responsive navigation,
    canonical progress presentation, and retained protected profile avatars
    are defined in decision 0025.
28. [Approved for Phase 21] Local-development LM Studio inference, the exact
    approved Qwen/gpt-oss allowlist and reasoning gate, strict local validation,
    exact model pinning, and controlled one-way Groq fallback are defined in
    decision 0026.

## Rule Approval

Status: Phase 2 decisions were approved on 2026-07-25. Phase 3 decisions were
approved on 2026-07-26 in decision 0008. Phase 4 course portions were approved
on 2026-07-27 in decision 0009. Phase 5 task portions were approved on
2026-07-27 in decision 0010. Phase 6 progress portions were approved on
2026-07-28 in decision 0011. Phase 7 was approved in decision 0012 and Phase 8
in decision 0013. Phase 9 was approved in decision 0014, Phase 10 in decision
0015, Phase 11 in decision 0016, Phase 14 in decision 0019, Phase 15 in
decision 0020, and Phase 16 in decision 0021. Remaining decisions still block
only separately approved extensions. Phase 17 was approved in decision 0022,
Phase 19 in decision 0024, Phase 20 in decision 0025, and Phase 21 in decision
0026.
