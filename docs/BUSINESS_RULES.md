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
16. [Approved for Phase 2] Accounts, departments, and audit events are not
    hard-deleted; expired throttle counters may be deleted. Later-domain
    exceptions remain open.
17. Which notification categories may users disable?
18. What retention periods apply to files, audit records, and archived data?
19. [Approved] Arabic is the default language, and each internal user may
    persist Arabic or English.
20. [Approved] The project owner approves official Arabic terminology.
21. Should Arabic display use Gregorian or Hijri dates and Arabic-Indic or
    Western digits in each output type?
22. [Approved for Phase 2] Preserve account identity text; apply NFKC to
    usernames and case-insensitive username/email comparison. Derived account
    search may ignore diacritics/tatweel and normalize Alef and Persian
    keyboard variants without merging `ة/ه` or `ى/ي`. Later duplicate policies
    remain open.

## Rule Approval

Status: Phase 2 decisions 16, 19, 20, and the account-search portion of 22 were
approved on 2026-07-25. Remaining decisions still block their listed phases.
