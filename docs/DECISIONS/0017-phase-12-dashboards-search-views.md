# Decision 0017: Phase 12 Dashboards, Search, and Operational Views

Status: Approved on 2026-07-29.

- Existing domain selectors remain the sole authorization boundary for every
  dashboard count, search section, board column, calendar item, and planning
  row. Role names select presentation labels only and never grant access.
- Dashboard cards show only metrics backed by an existing view permission.
  Project progress calls the centralized Phase 6 service; Phase 12 introduces
  no new formula, cached aggregate, or source-of-truth table.
- Global search covers visible projects, courses, tasks, and milestones. It
  uses the approved conservative Arabic normalization already maintained by
  each domain search key, requires at least two characters, and limits each
  result type to 25 displayed records.
- Saved filters are private to their owner, use schema version 1, accept only
  allowlisted query/date fields, and cannot be opened or deleted by another
  user. Sharing is deferred because no sharing policy is approved.
- Kanban is a read-only grouping of the existing Task status choices. Calendar
  includes visible project, course, task, milestone, and session dates.
  Timeline and Gantt are read-only. No drag/drop or planning edit endpoint is
  introduced.
- Planning ranges are limited to 92 days and shaped results to 200 items.
  Search and planning inputs are length/range validated before selectors run.
- User content is escaped by Django templates and mixed-direction identifiers
  are isolated with `bdi`. Arabic uses Bootstrap RTL and reviewed Arabic
  terminology; English uses the LTR asset.
- Reports, exports, editable Gantt/timeline, filter sharing, public search
  APIs, new business permissions, and speculative analytics remain outside
  Phase 12.
