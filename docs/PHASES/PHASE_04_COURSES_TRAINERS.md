# Phase 4: Courses and Trainers

Status: Draft; blocked by course lifecycle, permission, and time decisions.

## 1. Goal

Implement approved courses under projects, external trainer records,
schedules, capacity, files, and course lifecycle without trainees, sessions,
attendance, tasks, or progress calculation.

## 2. Included Features

- Course create, list/filter, detail, edit, archive/restore under permitted
  projects.
- External trainer records and approved contact data.
- Approved course status, schedule fields, capacity, description, and files.
- Authorized trainer assignment and course history/audit.
- Arabic/English course/trainer content, validation, filters, and RTL/LTR
  workflows.

## 3. Excluded Features

- Trainer internal accounts or general external portal.
- Trainee records/imports, individual sessions, attendance links/review.
- Course tasks and course progress.
- Notifications, dashboards, and reports.

## 4. User Stories

- As an authorized user, I can manage a course under a project I may access.
- As an authorized coordinator, I can maintain external trainer information
  and assign trainers.
- As a permitted viewer, I can see course information allowed by policy.
- As an unauthorized user, I cannot discover courses/trainers/files.

## 5. Models Involved

- `courses.Course`, `Trainer`, and approved trainer-assignment/schedule model.
- Approved course file relationships.
- Project foreign keys and audit/history records.

## 6. Pages Involved

- Course list/filter, create, detail, edit, archive/restore.
- Trainer list/create/detail/edit/archive as approved.
- Trainer assignment, schedule/capacity, and course-file sections.

## 7. Permission Requirements

Course access inherits or refines approved project access. The action matrix
must explicitly cover courses, trainers, trainer contact data, files, archive/
restore, and cross-project visibility.

## 8. Validation Rules

- Course belongs to an accessible non-archived project as approved.
- Dates/times, capacity, status transitions, trainer eligibility, duplicate
  trainers, and file rules follow approved policy.
- Personal contact data is visible only to approved roles.
- Arabic names/content preserve original text and use only approved
  normalization for duplicate/search behavior.

## 9. Business Rules

- Important course/trainer records use approved archive behavior.
- Project/course status transitions and date/time semantics remain unresolved.
- Course progress is explicitly deferred to Phase 6.

## 10. Expected Migrations

- Initial course/trainer/assignment or schedule models.
- Approved status, capacity, archive, file, and audit fields.
- Constraints/indexes for project, trainer, status, dates, and archive filters.

## 11. Unit Tests

- Course/trainer forms.
- Capacity, schedule, assignment, duplicate, status, and archive validation.
- Permission policy helpers.
- Localized course/trainer labels, validation, and mixed-direction contacts.

## 12. Integration Tests

- Authorized CRUD/archive/restore.
- Project-scoped course access and cross-project denial.
- Trainer personal-data/file authorization.
- Constraints, audit/history, and list query counts.
- Arabic course/trainer search and round-trip behavior.

## 13. Browser Tests

- Create/edit/archive a fictional Arabic course and assign an Arabic-named
  trainer in RTL; verify representative English LTR behavior.
- Verify permitted and restricted views.
- Verify schedule/capacity validation and file behavior.

## 14. Security Tests

- Direct course/trainer/file URL access.
- Cross-project form tampering.
- Personal contact data leakage.
- Upload validation, CSRF, and unauthorized state transitions.

## 15. Manual Verification

- Manage a course under a permitted project.
- Assign and update a fictional external trainer.
- Verify archive, files, schedule/capacity, and restricted access.
- Review Arabic terminology and mixed-direction emails, dates, and codes.

## 16. Acceptance Criteria

- Approved course/trainer lifecycle works under project authorization.
- Schedule/capacity/status/file validation is enforced.
- Personal trainer information is protected.
- Archive and audit/history behavior matches approved policy.
- No trainees, attendance, tasks, or progress are implemented.
- Arabic/English course and trainer workflows pass localization verification.

## 17. Dependencies

- Completed Phase 3.
- Approved course fields/status transitions, time semantics, duplicate trainer
  policy, project/course permission matrix, files, and archive rules.
- Approved Arabic terminology, date/digit display, and trainer duplicate/
  search normalization.

## 18. Rollback Considerations

- Preserve course/trainer history and uploaded-object references.
- Do not drop schedule/contact fields without export/backfill approval.
- Changes to project-course ownership require a safe data migration and
  authorization review.
