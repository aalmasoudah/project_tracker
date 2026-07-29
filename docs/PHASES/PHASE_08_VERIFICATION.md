# Phase 8 Verification

Verified on 2026-07-29.

## Completed Acceptance Criteria

- Manual trainee enrollment supports create, view, edit, archive, and restore
  inside approved course scope.
- Full name and phone duplicate identity is course-scoped, conservatively
  normalized, database-constrained, and preserves original Arabic/English
  source text.
- Course-specific trainee numbers are positive, immutable, allocated in source
  order, and never reused.
- UTF-8 CSV and XLSX imports validate before writes and present valid, warning,
  duplicate, and error outcomes.
- Confirmation requires explicit duplicate resolution, locks the course,
  rechecks capacity/identity, and writes the complete import atomically.
- Source files are not retained. Protected batch/row evidence and audit events
  contain no raw file bytes.
- Executive Manager, owning Project Manager, CEO, and Supervisor visibility
  follows decision 0013; contact information and import rows are not exposed to
  limited roster viewers.
- Arabic headers, values, errors, RTL presentation, and English LTR rendering
  are implemented.

## Migrations

- `audit.0006_alter_auditevent_scope`
- `trainees.0001_initial`
- `trainees.0002_seed_phase8_permissions`
- `trainees.0003_importbatch_warning_count_and_more`
- `trainees.0004_courseenrollment_trainees_identity_key_not_blank_and_more`

The migration plan and generated PostgreSQL SQL were reviewed before local
application.

## Automated Verification

- Ruff formatting and linting: passed.
- mypy: passed across 141 source files.
- Django system checks: passed.
- Migration drift check: passed.
- Arabic catalog: 655 messages, 0 untranslated; compilation passed.
- Unit and integration regression suite: 88 passed, 8 browser tests deselected.
- Browser suite: 8 passed, including the Phase 8 Arabic mobile workflow.
- Enrollment list reads trainee/course/project data in one bounded query.

## User-Like Browser Simulation

At a 390 by 844 mobile viewport, an Arabic Project Manager opened the trainee
import page, selected a managed course, uploaded a UTF-8 CSV with approved
Arabic headers and fictional Arabic data, reviewed the RTL preview, and
confirmed it. The preview displayed the row without creating an enrollment;
confirmation created the enrollment and preserved the Arabic name. Existing
English LTR browser coverage continued to pass.

## Security Review

Tests cover spoofed MIME types, oversized files, malformed/formula XLSX,
course-scope isolation, contact-data hiding, unauthorized import history,
duplicate constraints, capacity rollback, and no-write preview behavior.
Spreadsheet macros/external links and excessive decompressed content are
rejected. All mutations retain Django CSRF and method protections.

## Deferred

Sessions, trainer links, attendance, notifications, and reports remain in
their assigned later phases.

Recommended commit message: `feat: implement phase 8 trainees and imports`
