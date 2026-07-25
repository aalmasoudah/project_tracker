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

## Object-Level Access Questions

1. [Approved for Phase 2] Use the account/department scopes above. Later
   domain scopes are approved in their phases.
2. Can project managers access projects they do not manage?
3. [Approved for Phase 2] No. Supervisors see active users only in their own
   department.
4. Can employees and contractors see budgets?
5. Who may view personal attendance information?
6. Who may export reports containing personal data?
7. [Approved for Phase 2] Technical Admin may archive/restore departments.
   Accounts are deactivated/reactivated. Later records remain open.
8. [Approved for Phase 2] Technical Admin may read Phase 2 audit records.
   Detailed operational health remains deferred.

## Role Approval

Status: The role model and Phase 2 permission slice were approved on
2026-07-25. Later-domain matrix entries remain open.
