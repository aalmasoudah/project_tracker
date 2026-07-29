# User Roles

## Approved Predefined Roles

The following Phase 2 internal roles were approved on 2026-07-25:

- Technical Admin
- CEO
- Executive Manager
- Project Manager
- Supervisor
- Employee
- Contractor

Each internal account has exactly one managed predefined role. External
Trainer remains a stable business label but is not an internal account or
Django group.

## Role Model

- Internal roles use Django Groups as the initial role mechanism.
- Permissions must be checked at both view and object level.
- Navigation may reflect permissions, but hiding a link is never a security
  control.
- Accounts are created by an authorized administrator.
- Inactive users cannot sign in.
- Role assignment and account lifecycle changes are audited.
- External trainers use secure, limited, expiring links for approved
  attendance workflows and are not assumed to have internal accounts.
- Only a Django superuser may grant or revoke Technical Admin.
- Technical Admin may assign only non-technical managed roles.

## Phase 2 Permission Matrix

Permissions are approved incrementally by phase. Later-domain permissions
remain unresolved until their workflows are approved.

| Role | Accounts | Departments | Audit |
| --- | --- | --- | --- |
| Technical Admin | Create, view, update, deactivate/reactivate, reset passwords, assign non-technical roles | Create, view, update, archive/restore | Read |
| CEO | View all active directory entries | View all active departments | None |
| Executive Manager | View all active directory entries | View all active departments | None |
| Project Manager | View active users in own department | View own department | None |
| Supervisor | View active users in own department | View own department | None |
| Employee | View own profile | View own department | None |
| Contractor | View own profile | View own department | None |

All internal users may change their own password and language preference.
There are no Phase 2 approve or export actions. The public `/health/` endpoint
remains minimal; detailed operational information is deferred.

## Phase 3 Permission Matrix

| Role | Project visibility | Project changes | Budget | Archive/history |
| --- | --- | --- | --- | --- |
| Technical Admin | None | None | None | Phase 2 security audit only |
| CEO | All | None | All | View archived and all project history |
| Executive Manager | All | Full administration, references, teams, and statuses | All | Archive/restore any; all history |
| Project Manager | Managed projects | Create and manage own projects and teams | Managed projects | Archive/restore/history for managed projects |
| Supervisor | Active supervised/member projects | None | None | None |
| Employee | Active member projects | None | None | None |
| Contractor | Active member projects | None | None | None |

Every project belongs to one department. Managers, supervisors, and team
members must be active, have an eligible role, and belong to that department.
Executive Manager manages clients and categories. Project Managers select
active reference records but do not administer them.

## Phase 4 Permission Matrix

| Role | Course visibility | Course changes | Trainer contact/administration |
| --- | --- | --- | --- |
| Technical Admin | None | None | None |
| CEO | All, including archived, files, and history | None | View all contact data |
| Executive Manager | All | Full course, assignment, file, archive, and restore management | Full trainer administration |
| Project Manager | Courses in managed projects | Manage courses, assignments, files, archive, and restore | View active trainers and contact data |
| Supervisor | Active courses through approved active-project access | None | Trainer names only |
| Employee | Active courses through approved active-project access | None | Trainer names only |
| Contractor | Active courses through approved active-project access | None | Trainer names only |

## Phase 5 Permission Matrix

| Role | Task visibility | Task changes and collaboration | Tags/history |
| --- | --- | --- | --- |
| Technical Admin | None | None | None |
| CEO | All, including archived and files | Read only | View tags and all task history |
| Executive Manager | All | Full task, assignment, comment, file, archive, and restore management | Full tag administration and all history |
| Project Manager | Tasks in managed project/course contexts | Full management in those contexts | Full tag administration and managed-task history |
| Supervisor | Tasks in visible active contexts | Comment/upload; update status, actual hours, and block reason only when assigned | View tags; no history |
| Employee | Assigned tasks in active contexts | Comment/upload; update status, actual hours, and block reason | View tags; no history |
| Contractor | Assigned tasks in active contexts | Comment/upload; update status, actual hours, and block reason | View tags; no history |

## Phase 6 Progress Visibility

| Role | Task progress | Course progress | Project progress |
| --- | --- | --- | --- |
| Technical Admin | None | None | None |
| CEO | All visible records | All visible records | All visible records |
| Executive Manager | All visible records | All visible records | All visible records |
| Project Manager | Managed contexts | Managed contexts | Managed projects |
| Supervisor | Complete visible contexts | Active visible courses | Active visible projects only when every course source is visible |
| Employee | None | None | None |
| Contractor | None | None | None |

Phase 6 adds no permission codenames. It derives progress visibility from
approved source-record permissions and withholds a value whenever the actor's
scope might omit hierarchy or aggregate inputs.

## Phase 7 Milestone and Approval Matrix

| Role | Milestones | Submit completion | Approve/reject | History |
| --- | --- | --- | --- | --- |
| Technical Admin | None | None | None | Phase 2 security audit only |
| CEO | View all, including archived | None | None | View all requests and decisions |
| Executive Manager | Full administration | Any eligible item | Assigned step | View all requests and decisions |
| Project Manager | Manage milestones in managed projects | Eligible items in managed projects | Assigned Project Manager step | Managed-project history |
| Supervisor | View active visible milestones | Assigned eligible tasks | Assigned Supervisor step | Active visible context only |
| Employee | None | Assigned eligible tasks | None | Own submitted requests only |
| Contractor | None | Assigned eligible tasks | None | Own submitted requests only |

Approval is strictly sequential: an assigned Supervisor completes step one,
then an assigned Project Manager completes step two. The same person cannot
fill both steps. Rejection requires a reason, and immutable decisions remain
available only within the approved object scope.

## Phase 8 Trainee and Import Matrix

| Role | Roster visibility | Contact data | Changes/imports | History |
| --- | --- | --- | --- | --- |
| Technical Admin | None | None | None | Phase 2 security audit only |
| CEO | All names/numbers, including archived | None | None | None |
| Executive Manager | All | Full | Full lifecycle, preview, and confirm | All import history |
| Project Manager | Managed-project courses | Full | Full lifecycle, preview, and confirm in managed courses | Managed-course imports |
| Supervisor | Active visible course names/numbers | None | None | None |
| Employee | None | None | None | None |
| Contractor | None | None | None | None |

Import upload does not bypass course scope. Only Executive Managers and the
owning Project Manager receive both preview and confirmation permission.

## Object-Level Access Questions

1. [Approved through Phase 8] Use the account/department, project, course,
   task, milestone, approval, trainee, import, and progress scopes above.
   Later domains remain open.
2. [Approved for Phase 3] Project Managers cannot access projects they do not
   manage unless a later phase grants a separate assignment.
3. [Approved through Phase 8] Supervisors do not receive cross-department
   directory, project, course, task, milestone, approval, trainee, or import
   access.
4. [Approved for Phase 3] Employees and Contractors cannot see budgets.
5. Who may view personal attendance information?
6. Who may export reports containing personal data?
7. [Approved through Phase 8] Technical Admin may archive/restore departments.
   Executive Manager may archive/restore any project; Project Manager may do
   so only for a managed project. Accounts are deactivated/reactivated. Later
   records remain open.
8. [Approved for Phase 2] Technical Admin may read Phase 2 audit records.
   Detailed operational health remains deferred.

## Role Approval

Status: The role model and Phase 2 permission slice were approved on
2026-07-25. The Phase 3 project slice was approved on 2026-07-26 in decision
0008. The Phase 4 course/trainer slice was approved on 2026-07-27 in decision
0009. The Phase 5 task/collaboration slice was approved on 2026-07-27 in
decision 0010. The Phase 6 progress-visibility slice was approved on
2026-07-28 in decision 0011. The Phase 7 milestone/approval slice was approved
on 2026-07-28 in decision 0012. The Phase 8 trainee/import slice was approved
on 2026-07-29 in decision 0013. Later-domain matrix entries remain open.
