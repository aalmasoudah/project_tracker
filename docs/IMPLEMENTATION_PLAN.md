# Implementation Plan

## Planning Outcome

Status: Planning pass completed on 2026-07-23. Phases 1 through 8 are completed.
The project owner approved the remaining phases on 2026-07-29; each phase must
still resolve and record its blocking decisions before implementation.

The project proceeds one approved phase at a time. The approved scope permits
planning, but it does not approve unresolved business rules, permissions, or
phase specifications.

## Delivery Sequence

| Phase | Outcome | Depends on | Approval status |
| --- | --- | --- | --- |
| 1 | Engineering Foundation | Approved scope and technical plan | Completed on 2026-07-23 |
| 2 | Accounts, Roles, and Organization | Phase 1; Phase 2 permission slice | Completed on 2026-07-25 |
| 3 | Projects and Teams | Phase 2; project access/status/currency rules | Completed on 2026-07-26 |
| 4 | Courses and Trainers | Phase 3; course lifecycle/access rules | Completed on 2026-07-27 |
| 5 | Tasks and Collaboration | Phases 3-4; task rules | Completed on 2026-07-27 |
| 6 | Progress Engine | Phase 5; available progress formulas | Completed on 2026-07-28 |
| 7 | Milestones and Approvals | Phase 6; approval actors/steps | Completed on 2026-07-29 |
| 8 | Trainees and Imports | Phase 4; duplicate/import/privacy rules | Completed on 2026-07-29 |
| 9 | Sessions and Trainer Links | Phase 8; time/token/attendance rules | Blocked by business decisions |
| 10 | Attendance Approval and Corrections | Phase 9; actor/value rules | Blocked by business decisions |
| 11 | Notifications and Background Jobs | Relevant event-producing phases; preference rules | Blocked by business decisions |
| 12 | Dashboards, Search, and Operational Views | Core domains and approved permissions | Blocked by business decisions |
| 13 | Reports and Exports | Central progress services and report permissions | Blocked by business decisions |
| 14 | Administration, Audit, and Operational Safety | Prior audit/archive behavior; retention policy | Blocked by business decisions |

Independent preparatory research may occur, but implementation may not skip
dependencies or start a later phase without explicit approval.

## Decision Register

The following identifiers summarize, but do not replace, the source
requirements.

| ID | Required decision | Source | First blocking phase |
| --- | --- | --- | --- |
| BR-01 | Maximum task nesting depth | `BUSINESS_RULES.md` question 1 | Approved |
| BR-02 | Task statuses and completion statuses | Question 2 | Approved |
| BR-03 | Cancelled-task denominator behavior | Question 3 | Approved |
| BR-04 | Task progress formula | Question 4 | Approved |
| BR-05 | Course progress formula | Question 5 | Approved |
| BR-06 | Milestone/project progress formula | Question 6 | Project approved; milestone deferred to Phase 7 |
| BR-07 | Whether progress may exceed 100 percent | Question 7 | Approved |
| BR-08 | Project/course status transitions | Question 8 | Project and course slices approved |
| BR-09 | Milestone/project completion approval steps | Question 9 | Approved for Phase 7 |
| BR-10 | Reject/reopen/correct/override actors | Question 10 | Phase 7 approved; attendance actors remain open |
| BR-11 | Trainee/import duplicate identity | Question 11 | Approved |
| BR-12 | Allowed attendance values | Question 12 | 9 |
| BR-13 | Expiry during trainer data entry | Question 13 | 9 |
| BR-14 | Date/time storage, display, and overdue semantics | Question 14 | Phase 3-5 date/schedule slices approved; overdue remains open |
| BR-15 | Supported currencies and rounding | Question 15 | Phase 3 SAR budget slice approved |
| BR-16 | Hard-deletable records | Question 16 | Through Phase 5 approved; later records open |
| BR-17 | User-disableable notification categories | Question 17 | 11 |
| BR-18 | File/audit/archive retention periods | Question 18 | 14 |
| RBAC-01 | Phase-specific action-by-role permission matrix | `USER_ROLES.md` | Through Phase 8 approved |
| RBAC-02 | Assigned/department/all-record visibility | Object access question 1 | Through Phase 8 approved |
| RBAC-03 | Project-manager cross-project access | Question 2 | Approved |
| RBAC-04 | Supervisor cross-team/department access | Question 3 | Through Phase 8 approved |
| RBAC-05 | Employee/contractor budget visibility | Question 4 | Approved |
| RBAC-06 | Personal attendance visibility | Question 5 | 10 |
| RBAC-07 | Personal-data report export rights | Question 6 | 13 |
| RBAC-08 | Archive/restore authority | Question 7 | Through Phase 5 approved |
| RBAC-09 | Audit/health visibility | Question 8 | 14 |
| L10N-01 | Default language and preference persistence | `BUSINESS_RULES.md` question 19 | Approved |
| L10N-02 | Official Arabic terminology approver | Question 20 | Approved |
| L10N-03 | Calendar and digit display policy | Question 21 | Phase 3-5 date/schedule slices approved |
| L10N-04 | Arabic normalization for identity/search/duplicates | Question 22 | Account, project, course, trainer, task, and tag slices approved |

Phase owners must update the source documents when decisions are approved and
then revise the affected phase specification. A status or formula must never
be inferred from mockups, fixtures, or developer preference.

## Planning Conflicts Requiring Owner Resolution

These sequencing gaps exist in the approved playbook and have not been
silently resolved:

1. `SEQ-01`: Resolved in decision 0011. Phase 6 implements the centralized
   engine for available task/course/project models; Phase 7 extends it with
   milestones.
2. `SEQ-02`: Resolved in decision 0010 by deferring task approvals and reusable
   approval state machines to Phase 7.
3. `ALLOC-01`: Project files, custom fields, and templates were explicitly
   deferred from core Phase 3 in decision 0008 and require a separately
   approved extension.

Full Arabic support is an explicit later scope addition, not a conflict. It is
distributed across all user-visible phases and begins in Phase 1.

## Phase Workflow

For each phase:

1. Approve the phase file and all blocking decisions.
2. Create a `codex/`-prefixed phase branch unless the owner requests another
   branch convention.
3. Re-read the required documents and inspect existing code/tests.
4. Restate acceptance criteria, expected files/migrations, conflicts, and
   risks.
5. Implement only the approved scope with focused tests.
6. Run the complete phase quality gate.
7. Perform and record manual verification.
8. Review the Git diff and map criteria to evidence.
9. Obtain review, commit, push, and merge according to repository policy.
10. Stop before the next phase.

## Phase 1 Readiness

Phase 1 can proceed without choosing project/task/attendance business
behavior. Its specification is
`docs/PHASES/PHASE_01_ENGINEERING_FOUNDATION.md`.

Known setup risks observed on 2026-07-23:

- Docker 29.6.1 and Docker Compose 5.2.0 are available.
- `python` and `psql` were not available on the current shell `PATH`.
- The existing `.venv` Python launcher could not execute in the current
  sandbox and should be recreated or repaired during Phase 1.
- The repository already has `main`, an `origin` remote, and the initialization
  commit.
- Existing documentation changes are not yet committed.

These are engineering setup issues, not reasons to relax the Python 3.13 or
PostgreSQL requirements.

Phase 1 must also establish Arabic/English localization infrastructure, RTL/
LTR page shells, compiled translation catalogs, local Arabic-capable assets,
and bilingual browser smoke coverage. The default language remains
configurable until `L10N-01` is approved.

## Cross-Cutting Completion Gates

- Required automated and browser tests pass.
- Ruff formatting/linting and mypy pass.
- Django checks and `makemigrations --check` pass.
- Migrations and rollback considerations are reviewed.
- Permissions, object access, security behavior, and query efficiency are
  tested where applicable.
- Manual verification is recorded.
- Documentation and requirement traceability are current.
- No secrets, uploads, backups, or real company data are committed.
- No unrelated changes appear in the phase diff.
- Arabic/English translation, direction, mixed-content, and output checks pass
  for every affected acceptance criterion.

## Final Readiness Work

After Phase 14, perform the playbook's traceability, accessibility, security,
performance, UAT, Docker clean-install, staging, recovery-test, and production
launch gates. Production is not complete merely because all feature phases are
implemented.
