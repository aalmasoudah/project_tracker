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

## Rule Approval

Status: Phase 2 decisions were approved on 2026-07-25. Phase 3 decisions were
approved on 2026-07-26 in decision 0008. Phase 4 course portions were approved
on 2026-07-27 in decision 0009. Phase 5 task portions were approved on
2026-07-27 in decision 0010. Phase 6 progress portions were approved on
2026-07-28 in decision 0011. Phase 7 was approved in decision 0012 and Phase 8
in decision 0013. Phase 9 was approved in decision 0014, Phase 10 in decision
0015, Phase 11 in decision 0016, and Phase 14 in decision 0019. Remaining
decisions still block only separately approved extensions.
