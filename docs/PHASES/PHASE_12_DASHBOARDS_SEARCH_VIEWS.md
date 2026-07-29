# Phase 12: Dashboards, Search, and Operational Views

Status: Approved, implemented, and verified on 2026-07-29.

## 1. Goal

Implement role-specific dashboards, permission-aware global search, saved
filters, approval queues, Kanban, calendar, read-only timeline, and read-only
Gantt with measured query efficiency.

## 2. Included Features

- Executive, project-manager, supervisor, employee/contractor, and technical
  admin dashboards using approved metrics.
- Permission-aware global search and saved filters.
- Approved Kanban, calendar, timeline, Gantt, and approval queue views.
- Read-only Gantt/timeline unless later editing is explicitly approved.
- Arabic/English layouts, filters, search, dates, charts/labels, and RTL/LTR
  operational views.

## 3. Excluded Features

- New business formulas, statuses, permissions, or hidden data aggregation.
- Editable Gantt/timeline.
- Public search API, external analytics warehouse, or speculative dashboards.
- Reports/exports assigned to Phase 13.

## 4. User Stories

- As each approved role, I see only useful permitted cards, queues, and records.
- As a user, I can search/filter permitted records and save approved filters.
- As a manager, I can use operational views without changing data through
  read-only timeline/Gantt.
- As an Arabic-speaking user, I can search Arabic text and use all views in RTL.

## 5. Models Involved

- Existing domain models/selectors/progress services.
- `SavedFilter` with explicit owner, view type, validated schema, and safe
  versioning.
- No duplicate metric source-of-truth tables without an approved cache design.

## 6. Pages Involved

- Role dashboard routes.
- Global search results.
- Saved filter list/use/delete.
- Kanban, calendar, timeline, Gantt, and approval queue pages.

## 7. Permission Requirements

Every selector/aggregate uses approved actor scope. Search/autocomplete/counts,
saved filters, queues, and chart labels must not reveal restricted records.
Technical admin visibility follows the approved matrix, not role name alone.

## 8. Validation Rules

- Saved filter fields/operators/values are allowlisted and versioned.
- Dates/statuses/columns follow approved domain rules.
- Search normalization/sorting follow `L10N-04` without modifying stored text.
- Pagination and bounded date/range limits prevent unbounded queries.
- User-provided labels/content are escaped and direction-isolated.

## 9. Business Rules

- Metrics and progress call centralized services.
- Resolve role content, search scope, saved-filter sharing, Kanban rules,
  calendar dates, date/time policy, and Arabic normalization.
- Timeline/Gantt are read-only in the initial release.

## 10. Expected Migrations

- Saved filter model and approved constraints/indexes.
- Measured domain indexes or approved cache schema only when query evidence
  justifies them.

## 11. Unit Tests

- Dashboard card/metric policy.
- Search query parsing/normalization.
- Saved-filter schema validation/versioning.
- Kanban/calendar/timeline/Gantt data shaping and localized labels.

## 12. Integration Tests

- Role-specific content and aggregate authorization.
- Search results/counts/autocomplete do not leak restricted records.
- Filters/saved filters and view date/status rules.
- Query-count/performance tests with realistic synthetic volumes.
- Arabic search/sort/display behavior according to approved policy.

## 13. Browser Tests

- Log in as every role and inspect cards/queues.
- Search permitted/restricted Arabic and English records.
- Save/use/delete filters and open each operational view.
- Verify Arabic RTL and English LTR at common viewport/zoom sizes.

## 14. Security Tests

- Search enumeration, forged filters, shared filter ownership, aggregate count
  leakage, unsafe labels, direct object links, and excessive query ranges.
- Cached results, if any, are actor/permission safe and invalidated correctly.

## 15. Manual Verification

- Compare every metric to source records/central progress services.
- Verify role scopes and restricted searches.
- Review Arabic terminology, search variants, layout mirroring, dates, long
  labels, chart/table accessibility, and read-only behavior.

## 16. Acceptance Criteria

- Each role sees only approved, correct dashboard content.
- Search, filters, saved filters, queues, and operational views enforce object
  access and perform within approved budgets.
- Metrics use centralized formulas.
- Gantt/timeline are read-only.
- Arabic search/data and all RTL/LTR views pass localization/accessibility
  verification.

## 17. Dependencies

- Completed core domain, progress, approval, attendance, and notification
  phases as required by each view.
- Approved role content, permissions, metrics, statuses, dates, search/
  normalization, saved-filter, and performance requirements.
- Approved Arabic terminology/calendar/digit policy.

## 18. Rollback Considerations

- Saved-filter schema changes require compatibility/version migration.
- Remove indexes/caches only after confirming query/invalidations and mixed
  versions.
- Dashboard/view rollback must not alter source business records.
