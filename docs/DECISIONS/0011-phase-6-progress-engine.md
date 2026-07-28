# Decision 0011: Phase 6 Progress Engine

Date: 2026-07-28

Status: Approved

## Context

Phase 6 requires one calculation source for task, course, and project progress.
Milestones, task/course approvals, and attendance do not yet have approved
models, so their calculations cannot be implemented safely in this phase.

## Decision

- A non-archived, non-cancelled leaf task is 100 percent only when Completed;
  To Do, In Progress, and Blocked are 0 percent.
- Cancelled and archived tasks are excluded from aggregation with their whole
  branch. A non-cancelled parent averages its direct countable children
  recursively. If it has no countable children, its own leaf status applies.
- A non-archived, non-cancelled course averages its top-level task results.
  A course with no countable tasks is 0 percent with an explicit empty state.
- A non-archived, non-cancelled project equally averages the progress of
  categories that exist: direct project tasks and courses. Within each
  category, records have equal weight. A missing category is omitted.
- Cancelled or archived courses/projects return an excluded/not-applicable
  state. A project with no countable category returns an explicit empty
  0-percent state.
- Calculations use `Decimal`, remain unrounded internally, round only public
  results to two decimal places with `ROUND_HALF_UP`, and are bounded from
  0 through 100 percent.
- Estimated and actual hours do not affect progress. No editable or cached
  percentage is stored.
- Progress is shown only when the actor may see every underlying task source.
  Employee and Contractor do not receive task, course, or project progress
  values in Phase 6 because even a visible task can have hidden hierarchy.
- Arabic and English use the same numeric value. Phase 6 uses Gregorian/
  Western-digit percentage presentation with approved localized state labels.
- Milestone progress is deferred to Phase 7. Approval- and attendance-based
  course behavior is deferred until the relevant approved models exist.
- The Phase 5 hierarchy presentation is tightened so parent/subtask names and
  links are filtered through the actor's task visibility scope.

## Consequences

Phase 6 is calculation-first and requires no model field, cache, data
migration, approval UI, attendance dependency, dashboard, or report. Future
domains must extend this service instead of duplicating formulas.
