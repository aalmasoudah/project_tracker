# Decision 0013: Phase 8 Trainees and Imports

Status: Approved on 2026-07-29.

## Decision

- Trainees do not have accounts. Each course enrollment has an immutable,
  positive, course-specific number allocated in creation/import order.
- Full name and phone are required; email is optional. Original Arabic and
  English text is preserved.
- A duplicate exists only when the conservatively normalized full name and
  phone repeat in the same course. The same identity in another course is
  allowed.
- Saudi local `05...`, `+966...`, and `00966...` phone forms compare through
  one derived digit key. Stored phone text is not rewritten.
- Manual and imported enrollments cannot exceed active course capacity.
  Archived numbers are never reused.
- Imports accept UTF-8 CSV and macro-free XLSX only, up to 5 MiB and 5,000
  non-empty rows. Required headers are `full_name` and `phone`; `email` is
  optional. Approved Arabic aliases are included.
- XLSX imports must have one sheet. Formulas, macros, external links, malformed
  archives, and excessive decompressed content are rejected.
- Preview creates protected import evidence but no trainee/enrollment records.
  Errors block confirmation; missing optional email is a warning.
- Existing-course duplicates require explicit Skip or Update. Duplicates
  repeated inside the uploaded file can only be skipped. Confirmation locks
  the course and commits the complete valid resolution atomically.
- Executive Managers manage all course enrollments/imports. Project Managers
  manage only courses in projects they own. CEO and the active project
  Supervisor have read-only name/number rosters; contact fields are limited to
  Executive Managers and owning Project Managers. Employees, Contractors, and
  Technical Admin receive no Phase 8 trainee access.
- Enrollment/import history is protected. Source files are not retained after
  parsing. Trainees, enrollments, batches, rows, and audit history are not
  normally hard-deleted.

## Localization

Arabic headers and values are supported without altering source text. The
preview, validation, duplicate resolution, confirmation, archive lifecycle,
and privacy-limited roster are fully localized and direction-aware. Numbers
use Western digits.
