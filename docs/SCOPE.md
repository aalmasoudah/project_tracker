# Approved Scope

## Purpose

Create an internal system for managing company projects, courses, tasks,
trainees, attendance, approvals, progress, notifications, reports, and
operational audit records.

## In Scope

- Accounts, departments, predefined roles, and configurable permissions.
- Projects, teams, clients, categories, budgets, files, custom fields,
  templates, statuses, and archiving.
- Courses, external trainers, schedules, capacity, files, trainees, and
  course progress.
- Project tasks, course tasks, subtasks, assignments, dependencies,
  recurrence, approvals, comments, tags, and history.
- Milestones and multi-step project completion approvals.
- Trainee import, secure trainer links, attendance submission, approval,
  rejection, correction, and reporting.
- In-app notifications, email delivery, saved filters, global search,
  dashboards, Kanban, calendar, timeline, and read-only Gantt views.
- Approved PDF and Excel reports, audit logs, archive management, health
  checks, and documented recovery procedures.
- First-class Arabic and English localization across the application,
  including RTL/LTR layouts, validation, search, imports, notifications,
  operational views, and generated reports.

## Production-Oriented Constraints

- The first production release uses a Django monolith and PostgreSQL.
- The initial interface uses Django templates, Bootstrap, and HTMX.
- PostgreSQL is used in every environment.
- Important records are archived rather than normally deleted.
- Gantt and timeline views begin as read-only.
- Database restoration is an infrastructure operation, not a general web
  page action.
- Staging uses fictional or anonymized data and separate infrastructure.
- Arabic is supported from the engineering foundation rather than added only
  during report development.

## Explicitly Out of Scope for the Initial Release

- A separate React frontend.
- A public API unless approved by a later requirement.
- SMS and unrelated third-party messaging integrations.
- An unrestricted web-based database restoration feature.
- Editing Gantt or timeline data unless separately approved.
- Features that are not included in an approved phase specification.

## Delivery Phases

1. Engineering Foundation
2. Accounts, Roles, and Organization
3. Projects and Teams
4. Courses and Trainers
5. Tasks and Collaboration
6. Progress Engine
7. Milestones and Approvals
8. Trainees and Imports
9. Sessions and Trainer Links
10. Attendance Approval and Corrections
11. Notifications and Background Jobs
12. Dashboards, Search, and Operational Views
13. Reports and Exports
14. Administration, Audit, and Operational Safety

## Scope Approval

Status: Approved for planning, including the Arabic-support addition.

The project owner approved the original scope on 2026-07-23 and subsequently
added full Arabic support on the same date. Approval of this scope does not
approve unresolved business rules, localization policy details, the role
permission matrix, or any individual phase specification.
