# Business Rules

This file contains rules that affect calculations, approvals, permissions,
and record integrity. The development playbook intentionally does not define
all company-specific behavior, so unresolved rules are listed explicitly and
must be approved before their implementation phase.

## Confirmed Rules

- PostgreSQL is the system of record in all environments.
- Important business records are archived instead of normally deleted.
- Task nesting has a maximum approved depth. The exact number still requires
  approval; the playbook suggests three levels.
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

## Decisions Required Before Planning

The project owner must approve answers to these questions:

1. What is the exact maximum task nesting depth?
2. Which task statuses exist, and which statuses count as complete?
3. Do cancelled tasks contribute to progress denominators?
4. How is task progress calculated: status, checklist, manual percentage, or
   weighted work?
5. How is course progress calculated?
6. How are milestone and project progress calculated?
7. Can progress exceed 100 percent?
8. What are the project and course status transitions?
9. Which approval steps are required for milestone and project completion?
10. Who may reject, reopen, correct, or override each workflow?
11. What makes two trainees or imports duplicates?
12. What attendance values are allowed?
13. What happens when a trainer link expires during data entry?
14. Which dates and times are stored, displayed, and considered overdue?
15. Which currencies are supported, and how are monetary values rounded?
16. Which records may be hard-deleted, if any?
17. Which notification categories may users disable?
18. What retention periods apply to files, audit records, and archived data?
19. What is the default language, and may each user persist a preference?
20. Who approves official Arabic business terminology and translations?
21. Should Arabic display use Gregorian or Hijri dates and Arabic-Indic or
    Western digits in each output type?
22. Which Arabic normalization rules, if any, apply to identity, duplicate,
    sorting, and search behavior without altering stored original text?

## Rule Approval

Status: Incomplete. Development must not guess the unresolved rules.
