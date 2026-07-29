# Decision 0015: Phase 10 Attendance Approval and Corrections

Status: Approved on 2026-07-29.

- The assigned Supervisor of the active owning project is the only attendance
  reviewer. Approval and rejection are transactionally rechecked against that
  assignment and the active project/course/session scope.
- Rejection requires a reason, preserves an immutable decision snapshot, and
  reopens the same hash-only trainer token for 72 hours. Resubmission updates
  the current record and preserves every prior review snapshot.
- Approved attendance is read-only through the trainer capability link,
  including after the submission-time expiry of its editable state.
- Executive Managers may correct any approved attendance. The owning Project
  Manager may correct approved attendance in managed courses. Supervisors
  cannot correct their own reviewed records.
- Correction requires a reason and an immutable before/after snapshot. It does
  not change the approved state or create a new approval cycle.
- CEO, Executive Manager, owning Project Manager, and assigned Supervisor can
  view attendance only in their approved scopes. Employees and Contractors
  have no personal-attendance access in Phase 10.
- External trainer pages expose only locked trainee number/name and attendance
  data. Raw tokens, contact details, and unnecessary personal data are absent
  from review/correction audit metadata.
- Phase 10 dates use Gregorian dates, Western digits, and Asia/Riyadh time.
  Approved Arabic terms include Attendance Review `مراجعة الحضور`, Approved
  Attendance `الحضور المعتمد`, Correction `تصحيح`, and Correction Reason
  `سبب التصحيح`.
