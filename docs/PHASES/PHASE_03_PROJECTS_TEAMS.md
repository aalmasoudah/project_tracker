# Phase 3: Projects and Teams

Status: Draft; blocked by project, permission, time, and currency decisions.

## 1. Goal

Implement authorized project lifecycle, teams, clients, categories, approved
project metadata, files/custom fields/templates, and archive behavior without
adding courses, tasks, milestones, or progress.

## 2. Included Features

- Project create, view, edit, list/filter, archive, and approved restore flow.
- Clients, categories, approved priorities/statuses, dates, budgets, goals,
  requirements, notes, and other approved fields.
- Project manager, supervisor, and team membership.
- Approved project file, custom-field, and template behavior.
- Object-level project access and audit/history required by approved policy.
- Arabic/English fields, labels, validation, filters, files, and complete RTL/
  LTR project workflows.

## 3. Excluded Features

- Courses, tasks, milestones, approvals, progress calculations, dashboards,
  Kanban, calendar, Gantt, and reports.
- Status transitions or budget visibility not explicitly approved.
- Normal destructive deletion of important project records.

## 4. User Stories

- As an authorized project manager, I can create and maintain a permitted
  project and its team.
- As an assigned user, I can see only approved project information.
- As an authorized archivist, I can archive/restore projects according to
  policy.
- As an unauthorized user, I cannot discover a restricted project by list,
  search, file URL, or direct object URL.

## 5. Models Involved

- `projects.Project`, `Client`, `Category`, and `ProjectMembership`.
- Approved project status/priority representation.
- Approved project template and constrained custom-field definitions/values.
- `files.FileRecord` and explicit project-file relationship as required.
- Audit/history records.

## 6. Pages Involved

- Project list/filter, create, detail, edit, archive/restore.
- Client/category management.
- Team membership management.
- Approved project files/custom fields/templates.

## 7. Permission Requirements

Blocked until the action matrix plus `RBAC-02`, `RBAC-03`, `RBAC-04`,
`RBAC-05`, and `RBAC-08` are approved. Budget, file, archived-record, and team
membership access must be specified separately where needed.

## 8. Validation Rules

- Required fields, date ordering, status transitions, manager/supervisor role
  eligibility, team uniqueness, and ownership follow approved rules.
- Monetary values use approved currency and rounding.
- Custom fields are constrained by approved type/size definitions.
- Arabic project/client/category text preserves the original value; approved
  normalization is used only for search/duplicate behavior.
- Files pass size/extension/MIME validation and authorized storage access.
- Archived records are excluded or read-only according to policy.

## 9. Business Rules

- Important project records are archived rather than normally deleted.
- `BR-08`, `BR-14`, `BR-15`, `BR-16`, and project authorization decisions
  must be resolved before approval.
- No progress calculation is implemented.

## 10. Expected Migrations

- Initial project/client/category/membership models.
- Approved status/priority/template/custom-field/file relationships.
- Unique/check constraints and indexes for manager, team, archive, status,
  category, client, and date filters.

## 11. Unit Tests

- Project forms and date/money validation.
- Localized forms, status labels, pluralization, and mixed-direction values.
- Status-transition policy.
- Membership/role eligibility.
- Archive/restore and file/custom-field validation.

## 12. Integration Tests

- Authorized CRUD/archive/restore.
- Project queryset isolation and direct-object denial.
- Team changes and audit/history.
- Database constraints and file download authorization.
- Query-count coverage for project list/detail.
- Arabic filtering/sorting round-trip according to approved normalization.

## 13. Browser Tests

- Authorized user creates, edits, views, and archives a fictional Arabic
  project in RTL; representative English LTR coverage also passes.
- Team member sees permitted data.
- Restricted user cannot discover/open it.
- Validation and archive confirmation states render correctly.

## 14. Security Tests

- Horizontal/vertical project access.
- Budget/file/custom-field leakage.
- Form tampering with manager/team/status IDs.
- Upload validation, private download, CSRF, and method safety.

## 15. Manual Verification

- Exercise project lifecycle with each relevant approved role.
- Verify team visibility, budgets, archive/restore, and files.
- Inspect audit/history and restricted direct URLs.
- Review official Arabic project/status terminology and mixed-direction
  budgets, dates, files, and identifiers.

## 16. Acceptance Criteria

- Approved project fields and transitions are enforced.
- Only authorized users can discover or modify projects and related records.
- Team membership and role validation are correct.
- Important records use archive behavior.
- Upload/custom-field/template behavior is validated and audited as approved.
- No courses, tasks, milestones, or progress are implemented.
- Arabic/English project workflows and data pass localization verification.

## 17. Dependencies

- Completed Phase 2.
- Approved project schema, statuses/transitions, dates/timezone, currency/
  rounding, archive/hard-delete rules, files/custom fields/templates, and
  project permission matrix.
- Approved Arabic terminology, calendar/digit display, and project search/
  duplicate normalization.

## 18. Rollback Considerations

- Preserve project/team/history/file metadata.
- Use staged migrations for required fields or new constraints on existing
  rows.
- Stored objects must be cleaned only by an approved, auditable procedure;
  schema rollback must not orphan or expose files.
