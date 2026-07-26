# Decision 0008: Phase 3 Projects and Teams

- Status: Accepted
- Date: 2026-07-26
- Owner: Project owner

## Context

Phase 3 required an approved project schema, status workflow, object-level
permission slice, budget visibility, date and currency conventions, archive
behavior, team eligibility, audit visibility, and Arabic terminology.

The original development-plan PDF limits Phase 3 to core projects and teams
and explicitly defers custom fields. The draft repository specification had
also listed project files, custom fields, and templates. The owner approved
the smaller core phase, resolving that conflict in favor of deferral.

## Decision

### Scope

Phase 3 implements projects, clients, categories, and project memberships.
Project files, custom fields, and templates are deferred to a separately
approved extension. Courses, tasks, milestones, completion approvals,
progress, dashboards, and reports remain out of scope.

### Project Schema

- Project codes are immutable, case-insensitively unique ASCII identifiers.
- Arabic and English project names are required and preserved exactly except
  for harmless surrounding whitespace.
- Every project has one owning department and one required Project Manager.
- A Supervisor is optional.
- Client and category are optional archived reference records with immutable
  codes and required Arabic/English names.
- Start and end dates are required Gregorian date-only values. End date must
  not precede start date.
- Goals, requirements, and notes are optional user-authored text that may
  contain Arabic, English, or mixed-direction content.
- Budget is optional, non-negative, denominated only in SAR, and accepts at
  most two decimal places. Extra precision is rejected rather than silently
  rounded.

### Status and Priority

Stable project status codes and approved Arabic labels are:

| Code | English | Arabic |
| --- | --- | --- |
| `draft` | Draft | مسودة |
| `active` | Active | نشط |
| `on_hold` | On Hold | معلّق |
| `cancelled` | Cancelled | ملغى |

Allowed transitions are:

- Draft to Active or Cancelled.
- Active to On Hold or Cancelled.
- On Hold to Active or Cancelled.
- Cancelled to Draft.

There is no completed status in Phase 3. Completion is introduced only with
the approved Phase 7 completion workflow.

Stable priority codes and labels are:

| Code | English | Arabic |
| --- | --- | --- |
| `low` | Low | منخفضة |
| `medium` | Medium | متوسطة |
| `high` | High | عالية |
| `critical` | Critical | حرجة |

### Team Eligibility

- The manager must be an active Project Manager in the owning department.
- The optional supervisor must be an active Supervisor in that department.
- Team members must be active Project Managers, Supervisors, Employees, or
  Contractors in that department.
- A user has at most one active membership per project.
- Membership removal is timestamped and audited rather than hard-deleted.

### Permission Slice

- Superusers remain the recovery boundary and may access every Phase 3 action.
- CEO may view every project, budget, archived project, and project history.
- Executive Manager may create and manage every project, reference record,
  team, status, budget, archive, and restore action.
- Project Manager may create projects and manage only projects for which they
  are the manager, including budget and team membership.
- Supervisor may view active projects they supervise or join, without budget.
- Employee and Contractor may view active projects with an active membership,
  without budget.
- Technical Admin has no project-business access. Technical Admin continues
  to see Phase 2 security/account/department audit only.
- Executive Manager may archive/restore any project. A Project Manager may
  archive/restore only a project they manage.
- Only Executive Manager manages clients and categories; Project Manager may
  select active reference records.

Archived projects are read-only except for an authorized restore action.
Archived clients/categories cannot be selected. A client or category with an
active project cannot be archived.

### Audit and History

Audit events receive an explicit stable scope. Existing Phase 2 events are
classified as `security`; project, client, category, status, archive, and team
events are classified as `projects`.

CEO and Executive Manager may view all project history. A Project Manager may
view history only for a project they manage. Other roles have no Phase 3
history access. Technical Admin's existing audit page remains restricted to
the security scope.

### Localization

- Phase 3 uses Gregorian dates and Western digits in Arabic and English.
- Derived project/client/category search uses the approved conservative
  Arabic normalization from account search: ignore diacritics and tatweel,
  normalize Alef and Persian keyboard variants, and do not merge `ة/ه` or
  `ى/ي`.
- Original Arabic and mixed-direction content is never overwritten by search
  normalization.
- Stable codes are the identity boundary. Names are not silently treated as
  duplicates.

## Consequences

- Phase 3 can be implemented without guessing completion approval behavior,
  file security policy, custom-field limits, or template semantics.
- Phase 7 must add the completion status and approval-controlled transition.
- Files, custom fields, and templates require a future approved specification.
- Phase 3 requires an audit migration, an initial projects schema migration,
  and a reversible Phase 3 role-permission data migration.
