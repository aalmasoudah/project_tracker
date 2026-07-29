# Phase 7 Verification

Verified on 2026-07-29.

## Completed Acceptance Criteria

- Milestones support localized create, view, edit, archive, restore, and
  project-scoped visibility.
- Task, course, milestone, and project completion use one transactional,
  sequential Supervisor then Project Manager approval engine.
- Submission eligibility, assigned-step authorization, required rejection
  reasons, duplicate-decision prevention, and resubmission attempts are
  enforced in services and database constraints.
- Approval decisions are append-only, audit events are recorded, and pending
  source records cannot be edited or archived.
- Completed milestones contribute 100 percent through the centralized progress
  service, and projects include the equal-weight milestone category.
- Arabic and English queues, forms, validation, history, RTL/LTR layouts, and
  the responsive mobile workflow are implemented.

## Migrations

- `approvals.0001_initial`
- `approvals.0002_seed_phase7_permissions`
- `audit.0005_alter_auditevent_scope`
- `courses.0003_remove_course_courses_course_status_valid_and_more`
- `projects.0003_remove_project_projects_project_status_valid_and_more`

The migration plan and generated SQL were reviewed before application.

## Automated Verification

- Ruff formatting and linting: passed.
- mypy: passed.
- Django system checks: passed.
- Migration drift check: passed.
- Arabic catalog: 579 messages, 0 untranslated; compilation passed.
- Unit and integration regression suite: 78 passed, 7 browser tests deselected.
- Browser suite: 7 passed, including the Phase 7 Arabic mobile workflow.

## Manual Browser Simulation

At a 390 by 844 mobile viewport, a Project Manager created an Arabic
milestone, moved it to In Progress, and submitted it. The assigned Supervisor
approved step one and the assigned Project Manager approved step two. The
milestone became Completed and displayed 100 percent. The same pages were
checked in English LTR for direction switching and readable layout.

## Security Review

Direct URL access, wrong actor, wrong step, duplicate decisions, private
history, inactive source contexts, and pending-record mutation were covered by
tests. Mutations are POST-only and retain Django CSRF protection. Decisions
and audit history are not deleted by normal workflows.

## Incomplete or Deferred

Attendance approvals remain Phase 10. Notifications, broad dashboards,
reports, exports, and later operational controls remain in their assigned
phases.

Recommended commit message: `feat: implement phase 7 milestones and approvals`
