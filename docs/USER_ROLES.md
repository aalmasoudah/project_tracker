# User Roles

## Proposed Predefined Roles

The development playbook identifies the following user types for acceptance
testing. Their exact permissions require project-owner approval.

- Technical Admin
- CEO
- Executive Manager
- Project Manager
- Supervisor
- Employee
- Contractor
- External Trainer

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

## Permission Matrix Requiring Approval

For each role, approve Create, View, Update, Archive, Approve, Export, and
Administer permissions for:

- Users and departments
- Projects and teams
- Courses and trainers
- Tasks, comments, and files
- Milestones and completion approvals
- Trainees and imports
- Sessions and attendance
- Notifications
- Dashboards and search
- Reports and exports
- Audit and operational information

## Object-Level Access Questions

1. Can users view only assigned records, department records, or all records?
2. Can project managers access projects they do not manage?
3. Can supervisors access employees outside their department or team?
4. Can employees and contractors see budgets?
5. Who may view personal attendance information?
6. Who may export reports containing personal data?
7. Who may archive and restore each record type?
8. Who may view audit records and operational health information?

## Role Approval

Status: Proposed role list only. The permission matrix must be approved before
Phase 2.
