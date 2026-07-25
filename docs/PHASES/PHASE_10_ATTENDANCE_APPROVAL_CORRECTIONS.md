# Phase 10: Attendance Approval and Corrections

Status: Draft; blocked by attendance actor, value, permission, and correction
decisions.

## 1. Goal

Implement supervisor review, reasoned rejection with same-link reopening/new
expiry, approved read-only behavior, and authorized audited corrections
without reapproval.

## 2. Included Features

- Permission-scoped pending attendance queue and submission detail.
- Approve and reject transitions.
- Rejection reason, same logical trainer link reopened, and new expiry.
- Approved attendance read-only through trainer link.
- Authorized internal correction with required reason and audit entry, without
  restarting approval.
- Complete Arabic/English review, rejection, reopened external, and correction
  workflows.

## 3. Excluded Features

- Notifications/email, dashboards beyond the bounded queue, and reports.
- Unapproved override, bulk approval, reapproval, or value behavior.
- Editing approved attendance through the external trainer link.

## 4. User Stories

- As an authorized supervisor, I can review and approve/reject a permitted
  submission.
- As a trainer after rejection, I can reopen the same link with its new expiry,
  see the reason as approved, and resubmit.
- As an authorized corrector, I can correct approved attendance with a reason
  and complete audit trail without reapproval.
- As an Arabic-speaking participant, I can complete all relevant steps in RTL.

## 5. Models Involved

- Phase 9 submission/entry/trainer-link models.
- `AttendanceReview`/decision history and `AttendanceCorrection` or equivalent
  explicit immutable records.
- Audit events and approved actor references.

## 6. Pages Involved

- Pending queue, review detail, approve/reject confirmation.
- Reopened external trainer form and approved read-only view.
- Authorized correction form and correction/history display.

## 7. Permission Requirements

The matrix must identify reviewers by session/course/department/team, reject/
reopen actors, correction actors, personal attendance viewers, and audit
viewers. Correct permission is rechecked inside the transaction.

## 8. Validation Rules

- Only pending submissions may be approved/rejected; only approved entries may
  use the approved correction path.
- Rejection and correction require non-empty bounded reasons.
- Rejection reopens the same logical link and assigns a new approved expiry.
- Approved external state is read-only.
- Correction validates allowed attendance values and creates before/after
  evidence without reapproval.
- Arabic reasons preserve source text and render safely.

## 9. Business Rules

- Submission always requires supervisor approval.
- Rejection requires a reason and reopens the same link with a new expiration.
- Approved attendance is external-link read-only.
- Authorized correction requires reason/audit and no reapproval.
- Resolve `BR-10`, `BR-12`, `BR-13`, `BR-14`, personal-data permissions, and
  expiry durations.

## 10. Expected Migrations

- Attendance review/decision and correction/history models or safe additions.
- Constraints preventing conflicting current decisions and invalid states.
- Indexes for pending queues, reviewer scope, decision time, and correction
  history.

## 11. Unit Tests

- Approve/reject/correct state machine.
- Required reason and attendance value validation.
- New expiry calculation from approved policy.
- Localized status/reason/error presentation.

## 12. Integration Tests

- Submit/approve, submit/reject/reopen/resubmit/approve, and approved correction
  lifecycles.
- Concurrent/duplicate review/correction attempts.
- Same logical link/new expiry and approved external read-only behavior.
- Authorization, audit completeness, and no reapproval after correction.

## 13. Browser Tests

- Full rejection/reopen/resubmit/approve lifecycle in Arabic RTL.
- Approved external read-only view.
- Authorized/unauthorized correction and representative English LTR review.

## 14. Security Tests

- Wrong supervisor/course/session/corrector denial.
- Forged states/values/reasons, concurrent replay, token state, personal-data
  leakage, CSRF, and method safety.
- Audit/log output excludes raw tokens and unnecessary personal data.

## 15. Manual Verification

- Submit, reject, reopen, resubmit, and approve fictional attendance.
- Correct an approved entry and inspect history/audit/no reapproval.
- Verify unauthorized denials and Arabic terminology, reasons, dates, values,
  mixed names, and read-only state.

## 16. Acceptance Criteria

- Approval/rejection/correction exactly follows confirmed and newly approved
  rules.
- Rejection uses a required reason, same logical link, and new expiry.
- Approved external view is read-only.
- Correction is authorized, reasoned, audited, and does not trigger reapproval.
- Concurrency and object-level access are safe.
- Arabic/English attendance lifecycle passes localization verification.

## 17. Dependencies

- Completed Phase 9.
- Approved reviewer/corrector/override permissions, attendance values, expiry
  duration/semantics, personal-data visibility, and audit access.
- Approved Arabic attendance/rejection/correction terminology and date/digit
  policy.

## 18. Rollback Considerations

- Preserve all submissions, decisions, reasons, corrections, and token audit.
- Code rollback must understand states written by the newer version.
- Never restore editable external access to approved records as a rollback
  shortcut.
