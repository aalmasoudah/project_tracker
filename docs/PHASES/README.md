# Phase Specifications

One approved specification will be created for each development phase.

Each phase file must contain:

1. Goal
2. Included features
3. Excluded features
4. User stories
5. Models involved
6. Pages involved
7. Permission requirements
8. Validation rules
9. Business rules
10. Expected migrations
11. Unit tests
12. Integration tests
13. Browser tests
14. Security tests
15. Manual verification
16. Acceptance criteria
17. Dependencies
18. Rollback considerations

Phase specifications must not be generated as approved requirements until the
project owner resolves the open decisions in the core documents.

## Planning Register

| Phase | File | Planning status |
| --- | --- | --- |
| 1 | `PHASE_01_ENGINEERING_FOUNDATION.md` | Completed and verified on 2026-07-23 |
| 2 | `PHASE_02_ACCOUNTS_ROLES_ORGANIZATION.md` | Completed and verified on 2026-07-25 |
| 3 | `PHASE_03_PROJECTS_TEAMS.md` | Completed and verified on 2026-07-26 |
| 4 | `PHASE_04_COURSES_TRAINERS.md` | Completed and verified on 2026-07-27 |
| 5 | `PHASE_05_TASKS_COLLABORATION.md` | Completed and verified on 2026-07-27 |
| 6 | `PHASE_06_PROGRESS_ENGINE.md` | Completed and verified on 2026-07-28 |
| 7 | `PHASE_07_MILESTONES_APPROVALS.md` | Completed and verified on 2026-07-29 |
| 8 | `PHASE_08_TRAINEES_IMPORTS.md` | Completed and verified on 2026-07-29 |
| 9 | `PHASE_09_SESSIONS_TRAINER_LINKS.md` | Draft; blocked by attendance/time decisions |
| 10 | `PHASE_10_ATTENDANCE_APPROVAL_CORRECTIONS.md` | Draft; blocked by actor/value decisions |
| 11 | `PHASE_11_NOTIFICATIONS_BACKGROUND_JOBS.md` | Draft; blocked by notification decisions |
| 12 | `PHASE_12_DASHBOARDS_SEARCH_VIEWS.md` | Draft; depends on approved domain permissions |
| 13 | `PHASE_13_REPORTS_EXPORTS.md` | Draft; blocked by report/privacy decisions |
| 14 | `PHASE_14_ADMIN_AUDIT_OPERATIONS.md` | Draft; blocked by retention/operations decisions |

An approved phase must have its `Status` changed explicitly by the project
owner. Approval of `docs/SCOPE.md` or this planning pass does not implicitly
approve a phase.

Arabic/English localization is a cross-cutting approved scope requirement.
Every user-visible phase must satisfy `docs/LOCALIZATION.md` even when the
phase's primary domain is unrelated to translation.
