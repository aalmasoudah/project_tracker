# Phase 3: Projects and Teams

Status: Completed and verified on 2026-07-26.

## 1. Goal

Implement the approved project lifecycle, clients, categories, department
teams, budget visibility, archive behavior, and project history without
adding courses, tasks, milestones, completion, progress, or uploads.

## 2. Included Features

- Project create, view, edit, list/filter, archive, and restore.
- Bilingual clients and categories.
- Required owning department and Project Manager, optional Supervisor, and
  active project team membership.
- Approved statuses, priorities, Gregorian dates, SAR budget, goals,
  requirements, and notes.
- Approved object-level project access and scoped project history.
- Arabic/English labels, validation, filtering, and complete RTL/LTR project
  workflows.

## 3. Excluded Features

- Project files, custom fields, and templates, which decision 0008 defers to a
  separately approved extension.
- Courses, tasks, milestones, completion approvals, progress calculations,
  dashboards, Kanban, calendar, Gantt, and reports.
- A completed project status before the Phase 7 completion workflow.
- Destructive deletion of projects, clients, categories, or membership
  history.

## 4. User Stories

- As an Executive Manager, I can manage all projects, reference data, and
  project teams.
- As a Project Manager, I can create a project and manage only projects for
  which I am the manager.
- As a CEO, I can see all projects, budgets, archives, and project history.
- As an assigned user, I can see only active approved project information.
- As an unauthorized user, I cannot discover a restricted project by list,
  search, history, or direct object URL.

## 5. Models Involved

- `projects.Client`: immutable code, Arabic/English names, search key, and
  archive metadata.
- `projects.Category`: immutable code, Arabic/English names, search key, and
  archive metadata.
- `projects.Project`: immutable code; Arabic/English names; department;
  manager; optional supervisor/client/category; status; priority; start/end
  dates; optional SAR budget; goals; requirements; notes; search and archive
  metadata.
- `projects.ProjectMembership`: project/user relationship with timestamped
  addition and removal metadata.
- `audit.AuditEvent`: explicit `security` or `projects` scope.

## 6. Pages Involved

- Project list/filter, create, detail, edit, archive, and restore.
- Project team management.
- Client and category list/create/edit/archive/restore for Executive Manager.
- Permission-scoped project history.
- Base navigation updated only for approved project permissions.

## 7. Permission Requirements

The exact matrix is recorded in `USER_ROLES.md` and decision 0008.

- CEO views all projects, budgets, archives, and project history.
- Executive Manager fully manages all projects, references, teams, status,
  budget, archives, restores, and history.
- Project Manager creates projects and manages budget/team/status/archive/
  history only for a project they manage.
- Supervisor views active projects they supervise or join without budget.
- Employee/Contractor views active projects with active membership without
  budget.
- Technical Admin receives no project-business access and sees only the
  existing security audit scope.

Permissions are enforced in views, services, and permission-scoped selectors.
Inaccessible and nonexistent project identifiers return the same response.

## 8. Validation Rules

- Codes use 2-30 uppercase ASCII letters, digits, underscores, or hyphens,
  start with a letter, are immutable, and are case-insensitively unique.
- Arabic and English project/client/category names are required and preserved.
- Start and end dates are required; end cannot precede start.
- Budget is optional, non-negative SAR with at most two decimals. Extra
  precision is rejected.
- Manager must be an active Project Manager in the owning department.
- Supervisor must be an active Supervisor in the owning department.
- Team members must be active Project Managers, Supervisors, Employees, or
  Contractors in the owning department.
- One active membership exists per project/user; removal is end-dated.
- Archived projects are read-only except for restore.
- Archived clients/categories cannot be assigned and cannot be archived while
  referenced by an active project.
- Arabic search normalization is derived and never overwrites stored content.

## 9. Business Rules

Status codes:

- `draft`: may transition to Active or Cancelled.
- `active`: may transition to On Hold or Cancelled.
- `on_hold`: may transition to Active or Cancelled.
- `cancelled`: may transition to Draft.

Priority codes are `low`, `medium`, `high`, and `critical`.

Executive Manager may archive/restore any project. Project Manager may
archive/restore only a project they manage. Important records are never
hard-deleted through application paths. No progress or completion calculation
is implemented.

## 10. Expected Migrations

- Initial projects/client/category/membership models with approved constraints
  and indexes.
- Audit-event scope with existing Phase 2 events backfilled to `security`.
- Reversible Phase 3 group-permission assignment.

## 11. Unit Tests

- Project/reference forms, dates, money, statuses, and role eligibility.
- Status-transition policy.
- Archive/restore and membership validation.
- Localized status/priority labels and conservative Arabic normalization.

## 12. Integration Tests

- Authorized create/edit/status/archive/restore.
- Project queryset isolation and direct-object denial.
- Team changes and scoped audit history.
- Database constraints for codes, dates, money, and membership.
- Filtering, pagination, Arabic search round-trip, and query-count coverage.

## 13. Browser Tests

- Executive Manager creates and edits a fictional Arabic project in RTL.
- Project Manager manages a permitted project.
- Assigned user sees permitted fields without budget.
- Restricted user cannot discover/open the project.
- Mobile navigation, validation, filtering, and archive confirmation render
  correctly, with representative English LTR coverage.

## 14. Security Tests

- Horizontal and vertical project access.
- Budget and history leakage.
- Form tampering with department, manager, supervisor, member, status, client,
  and category identifiers.
- CSRF and method safety for state changes.
- Technical Admin does not gain business-project or project-history access.

## 15. Manual Verification

- Exercise project lifecycle as Executive Manager and Project Manager.
- Verify visibility as CEO, Supervisor, Employee, Contractor, and Technical
  Admin.
- Verify budget hiding, team scope, archive/restore, and project history.
- Review Arabic terminology, mixed-direction content, Gregorian dates,
  Western digits, responsive tables, and mobile RTL layout.

## 16. Acceptance Criteria

- Approved project fields and transitions are enforced.
- Only authorized users can discover or modify projects and reference records.
- Budget and project history visibility match the approved matrix.
- Team membership and role/department validation are correct.
- Projects and references use archive behavior; membership removal is
  end-dated.
- No files, custom fields, templates, courses, tasks, milestones, completion,
  or progress are implemented.
- Arabic and English project workflows pass localization and RTL/LTR
  verification.

## 17. Dependencies

- Completed Phase 2.
- Decision 0008 and the source-document updates approved on 2026-07-26.

## 18. Rollback Considerations

- Preserve projects, teams, references, history, and audit scope data.
- Role-permission data migration is reversible.
- Do not drop project data or remove audit history without a separately
  approved export/retention plan.
