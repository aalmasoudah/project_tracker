# Phase 9: Sessions and Trainer Links

Status: Completed and verified on 2026-07-29.

## 1. Goal

Implement scheduled course sessions, approved recurrence/capacity behavior,
cryptographically secure expiring trainer links, and external attendance
submission into pending supervisor review.

## 2. Included Features

- Session create/list/detail/edit/archive and approved recurrence generation.
- Course/trainer/trainee association and capacity validation.
- Random expiring trainer-link issue/reissue lifecycle with hashed tokens.
- Narrow external page to view the session and submit approved attendance
  values.
- Pending-review submission snapshot and audit/token events.
- Complete Arabic/English external trainer experience and RTL/LTR internal
  scheduling screens.

## 3. Excluded Features

- Supervisor approval/rejection/correction, which belongs to Phase 10.
- Email notification/delivery of links, reminders, dashboards, and reports.
- Internal trainer accounts or access beyond the capability link.
- Guessed expiry, attendance values, or recurrence semantics.

## 4. User Stories

- As an authorized coordinator, I can schedule a session and issue a limited
  link to its assigned trainer.
- As the external trainer holding a valid link, I can submit attendance only
  for the linked session.
- As an unauthorized/expired-link visitor, I receive a safe response and
  cannot infer protected data.
- As an Arabic-speaking trainer, I can complete every external step in Arabic
  RTL, including localized validation.

## 5. Models Involved

- `attendance.Session`, approved recurrence/source relation.
- `TrainerLink` with token hash, expiry, state, and lifecycle metadata.
- `AttendanceSubmission` and `AttendanceEntry` in pending-review state.
- Course, trainer, enrollment/trainee, and audit relationships.

## 6. Pages Involved

- Internal session list/calendar-bounded view, create, detail, edit, archive.
- Issue/reissue/revoke link action and safe one-time raw-link display.
- External token landing, attendance form, confirmation, expired/invalid/
  submitted/read-only states.

## 7. Permission Requirements

Internal session/link actions follow approved course scope. Raw links are
visible only at approved issuance time to authorized actors. External access
is limited to token-bound session data and cannot navigate internal pages.

## 8. Validation Rules

- Session dates/times, capacity, recurrence, trainer/course/enrollment
  eligibility, and overlaps follow approved rules.
- Tokens use secure randomness, hash lookup, explicit expiry/state, and replay
  prevention.
- Attendance values use approved `BR-12`.
- `BR-13` defines expiry during data entry and submission.
- Form rows exactly match authorized session trainees; forged/missing IDs are
  rejected.
- Arabic names/notes preserve source text and mixed direction is isolated.

## 9. Business Rules

- Attendance submission always enters supervisor review.
- Secure links are random and expiring; hashes are stored where practical.
- Decision 0014 resolves `BR-12`, `BR-13`, time, recurrence/capacity, actor,
  archive, evidence, token, and permission behavior.

## 10. Expected Migrations

- Initial session, recurrence/source, trainer link, submission, and entry
  models.
- Unique/check constraints for token hash, session/trainee entries, state, and
  recurrence identity.
- Indexes for course, trainer, date, archive, token hash, expiry, and review
  state.

## 11. Unit Tests

- Session/recurrence/capacity validation.
- Token generation, hashing, expiry, state transitions, and safe comparison.
- External attendance form and localized values/errors.
- Submission idempotency/replay handling.

## 12. Integration Tests

- Schedule/issue/open/submit pending-review lifecycle.
- Invalid, expired, revoked, reused, and forged links.
- Cross-session trainee tampering and atomic submission.
- Recurrence generation retry safety and query counts.
- Arabic content and localized external responses.

## 13. Browser Tests

- Authorized coordinator creates session/issues link.
- Trainer opens and submits through valid link in Arabic RTL.
- Representative English LTR submission passes.
- Invalid/expired/reused states are safe and localized.

## 14. Security Tests

- Token is sufficiently random, only hash is stored, raw token is absent from
  logs/history, and timing/state responses avoid useful enumeration.
- Forged trainee/session values, CSRF policy for capability forms, replay,
  clickjacking, caching/referrer leakage, and direct internal access.

## 15. Manual Verification

- Schedule one/recurring fictional sessions and verify capacity.
- Issue/open/submit a link; inspect pending state and audit without raw token.
- Test expiry/revocation/reuse and Arabic/English mixed trainee names.

## 16. Acceptance Criteria

- Approved session/recurrence/capacity rules are enforced.
- Link tokens are secure, expiring, narrowly scoped, and hash-stored.
- External submission is atomic, idempotent as approved, and always pending
  supervisor review.
- Unauthorized/expired/replayed access is safe.
- Arabic/English scheduling and external workflows pass localization review.

## 17. Dependencies

- Completed Phase 8 and course/trainer foundation.
- Approved attendance values, time/overdue semantics, recurrence, capacity,
  link lifetime, expiry-during-entry, token delivery actor, and permissions.
- Approved Arabic attendance terminology, dates/digits, and external wording.

## 18. Rollback Considerations

- Revoke outstanding tokens when a rollback cannot interpret their state.
- Preserve submitted attendance and token lifecycle audit.
- Recurrence rollback must not duplicate/delete sessions silently.
- Never expose stored token hashes as replacement raw links.
