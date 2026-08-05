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
- Permission-scoped, read-only AI project briefings generated asynchronously
  from approved structured evidence with source citations and human review.
- A CEO-only Arabic Telegram reporting integration orchestrated by n8n, using
  fixed commands, signed requests, named attendance PDFs, and critical-task
  alerts under the Phase 16 privacy boundary.
- A permission-scoped project recovery agent with allowlisted reads, cited
  reviewed memory, human-approved proposals, transactional idempotent
  execution through existing business services, and final verification under
  the Phase 17 boundary.
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
- A public API except the narrow signed Phase 16 and Phase 17 n8n integration
  endpoints.
- SMS and third-party messaging integrations other than the approved CEO-only
  Phase 16 Telegram workflow.
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
15. AI Project Briefings
16. CEO Telegram and n8n Executive Reports
17. Agentic Project Recovery and Planning

## Scope Approval

Status: Approved through the Phase 17 agentic project-recovery extension.

The project owner approved the original scope on 2026-07-23 and subsequently
added full Arabic support on the same date. Approval of this scope does not
approve unresolved business rules, localization policy details, the role
permission matrix, or any individual phase specification.

The project owner approved the Phase 15 AI Project Briefing extension and its
detailed implementation plan on 2026-08-04. This approval does not authorize
an unrestricted chatbot, autonomous business-record changes, or sending live
data to a provider before its deployment configuration is explicitly enabled.

The project owner approved the Phase 16 CEO Telegram/n8n extension and
explicitly approved trainee names in the bound CEO-chat attendance PDF on
2026-08-04. No other Telegram recipient, personal-data field, arbitrary bot
command, or external business-record write is authorized.

The project owner approved the Phase 17 agentic project-recovery extension on
2026-08-04. It authorizes only the allowlisted read tools and proposal types in
Decision 0022. No model may write directly; execution requires a separate
human approval, current underlying business permission, unchanged source
state, idempotent service execution, and final verification.
