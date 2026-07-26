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

## Object-Level Access Questions

1. [Approved through Phase 3] Use the account/department scopes above and the
   project scopes in the Phase 3 matrix. Later domains remain open.
2. [Approved for Phase 3] Project Managers cannot access projects they do not
   manage unless a later phase grants a separate assignment.
3. [Approved through Phase 3] Supervisors do not receive cross-department
   directory or project access.
4. [Approved for Phase 3] Employees and Contractors cannot see budgets.
5. Who may view personal attendance information?
6. Who may export reports containing personal data?
7. [Approved through Phase 3] Technical Admin may archive/restore departments.
   Executive Manager may archive/restore any project; Project Manager may do
   so only for a managed project. Accounts are deactivated/reactivated. Later
   records remain open.
8. [Approved for Phase 2] Technical Admin may read Phase 2 audit records.
   Detailed operational health remains deferred.

## Role Approval

Status: The role model and Phase 2 permission slice were approved on
2026-07-25. The Phase 3 project slice was approved on 2026-07-26 in decision
0008. Later-domain matrix entries remain open.
