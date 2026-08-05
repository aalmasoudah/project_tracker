# Decision 0018: Phase 13 Reports and Exports

Status: Approved on 2026-07-30.

- The approved catalog is limited to project progress (PDF/Excel), overdue
  tasks (Excel), course attendance summary (PDF/Excel), and project attendance
  summary (PDF/Excel). Individual attendance and personal-data exports are
  excluded.
- Each report has an explicit `reports.*` export permission. CEO and Executive
  Manager receive all four; Project Manager receives all four within managed
  scope; Supervisor receives only supervised attendance summaries. Employee,
  Contractor, and Technical Admin receive none.
- Existing project, course, task, attendance, and progress selectors/services
  remain the authorization and calculation boundary. Phase 13 introduces no
  role-name authorization checks, progress formula, or report source table.
- Reports are generated synchronously and entirely in memory, limited to 5,000
  rows and a 366-day filter range. Generated files, request metadata, history,
  public links, and scheduled delivery are not retained.
- Attendance output contains session/course aggregate totals only and omits
  trainee names, contact details, notes, evidence, and individual records.
- Every report supports an approved Arabic or English locale. Dates contain
  Gregorian and Umm al-Qura Hijri values using Western digits. Arabic Excel
  worksheets are RTL; Arabic PDFs use embedded Noto Sans Arabic with explicit
  shaping and bidi processing.
- Insight Projects / إنسايت بروجكتس branding is fixed from the owner-supplied
  logo. Deep green
  `#0A400C` is primary, sage `#819067` is secondary, and warm stone `#B1AB86`
  is limited to soft highlights.
- Excel cells beginning with `=`, `+`, `-`, or `@` are neutralized. Download
  filenames are fixed ASCII stems, responses are private/no-store, and no
  replayable download endpoint exists.
