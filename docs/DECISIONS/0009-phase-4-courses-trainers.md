# Decision 0009: Phase 4 Courses and Trainers

- Status: Accepted
- Date: 2026-07-27
- Owner: Project owner

## Context

Phase 4 required approval of course fields and lifecycle, schedule semantics,
trainer identity, object permissions, private files, archive behavior, Arabic
terminology, and search normalization. The original development plan confirms
that location, delivery type, capacity, schedule, statuses, files, notes,
external trainers, and course permissions belong to this phase.

## Decision

- Courses belong permanently to one project and have an immutable,
  case-insensitively unique ASCII code plus required Arabic and English names.
- Capacity is a positive integer. The required start and end values are
  timezone-aware datetimes entered and displayed in `Asia/Riyadh`; end must be
  later than start and both local dates must fall inside the project dates.
- Delivery types are `in_person`, `online`, and `hybrid`. Location is required
  for in-person and hybrid delivery.
- Course statuses are `draft`, `active`, `on_hold`, and `cancelled`, with the
  same transition graph as Phase 3 projects. Completion remains Phase 7.
- A course may become active only while its project is active. A project
  cannot leave Active while it has an active course and cannot be archived
  while it has an unarchived course.
- Trainers are external records without accounts. Their immutable code and
  required email are case-insensitively unique, including archived records.
  Arabic and English names are required; phone, organization, and notes are
  optional.
- Courses may have multiple active trainers. Assignments are end-dated rather
  than deleted. Archiving a course end-dates its active assignments.
- CEO has read access to all course, file, history, and trainer-contact data.
  Executive Manager has full management. Project Manager manages courses,
  files, and assignments only in managed projects and may view active trainer
  contact data. Supervisor, Employee, and Contractor see active courses and
  files only through their approved active project access and do not see
  trainer contact data. Technical Admin has no course-business access.
- Courses and trainers are archived, never hard-deleted. Archived records are
  read-only. A trainer with an active assignment cannot be archived.
- Course files are private PDF, DOCX, XLSX, PPTX, PNG, or JPEG files up to
  25 MiB. Extension, declared MIME type, and signature/container structure are
  validated. Storage keys are random, downloads are authorized and forced as
  attachments, and production uses private S3-compatible storage.
- Phase 4 uses Gregorian dates, Western digits, Riyadh time, and the approved
  conservative Arabic normalization without changing original content.
- Course, trainer, assignment, status, archive, restore, and file actions are
  recorded in the append-only `courses` audit scope.

## Consequences

Trainees, sessions, attendance links, tasks, course progress, completion, and
notifications remain out of scope. Phase 9 session timestamps must fall
inside the approved course schedule.
