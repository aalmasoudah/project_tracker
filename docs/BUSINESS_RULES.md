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
9. Which approval steps are required for milestone and project completion?
10. Who may reject, reopen, correct, or override each workflow?
11. What makes two trainees or imports duplicates?
12. What attendance values are allowed?
13. What happens when a trainer link expires during data entry?
14. [Approved for Phase 3 date-only project fields, Phase 4 Riyadh course
    schedules, and Phase 5 date-only task fields] Which dates and times are
    stored, displayed, and considered overdue? Task overdue rules remain open.
15. [Approved for Phase 3 project budgets] Which currencies are supported,
    and how are monetary values rounded? Later monetary outputs remain open.
16. [Approved through Phase 5] Accounts, departments, audit events, projects,
    clients, categories, courses, trainers, tasks, tags, comments, and files
    are not hard-deleted; memberships and assignment/tag relationships are
    end-dated. Expired throttle counters may be deleted. Later-domain
    exceptions remain open.
17. Which notification categories may users disable?
18. What retention periods apply to files, audit records, and archived data?
19. [Approved] Arabic is the default language, and each internal user may
    persist Arabic or English.
20. [Approved] The project owner approves official Arabic terminology.
21. [Approved for Phase 3 through Phase 5 screens] Should Arabic display use
    Gregorian or Hijri dates and Arabic-Indic or Western digits in each output
    type? Later outputs remain open.
22. [Approved through Phase 5 search/identity slices] Preserve account
    identity text; apply NFKC to
    usernames and case-insensitive username/email comparison. Derived account
    search may ignore diacritics/tatweel and normalize Alef and Persian
    keyboard variants without merging `ة/ه` or `ى/ي`. Later duplicate policies
    remain open.

## Rule Approval

Status: Phase 2 decisions were approved on 2026-07-25. Phase 3 decisions were
approved on 2026-07-26 in decision 0008. Phase 4 course portions were approved
on 2026-07-27 in decision 0009. Phase 5 task portions were approved on
2026-07-27 in decision 0010. Phase 6 progress portions were approved on
2026-07-28 in decision 0011. Remaining decisions still block their listed
phases.
