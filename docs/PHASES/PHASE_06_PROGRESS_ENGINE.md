# Phase 6: Progress Engine

Status: Completed and verified on 2026-07-28.

## 1. Goal

Create one centralized, tested progress engine for tasks, courses, projects,
and—once its model exists—milestones, so dashboards and reports cannot invent
or duplicate calculations.

## 2. Included Features

- Approved task, course, and project progress formulas.
- Cancelled-item denominator behavior and percentage bounds.
- Service interfaces with explicit inputs/outputs and Decimal-safe behavior
  where weighting is approved.
- Selectors/query helpers that avoid N+1 queries.
- Localized display formatting separated from numeric calculation.

## 3. Excluded Features

- Milestone model/approval UI unless sequencing is explicitly changed.
- Dashboards, notifications, reports, and editable stored percentages.
- Any guessed formula, weight, status mapping, or rounding.

## 4. User Stories

- As an authorized user, I see the same approved progress value everywhere.
- As a developer, I call one service rather than reimplementing formulas.
- As an Arabic or English user, I see the same numeric result with only
  approved localized presentation differences.

## 5. Models Involved

- Existing `tasks.Task`, `courses.Course`, and `projects.Project`.
- `approvals.Milestone` remains deferred to Phase 7.

Progress remains calculated unless an approved caching design proves necessary.

## 6. Pages Involved

- Existing task/course/project detail pages may show approved progress.
- No new dashboard/report page.

## 7. Permission Requirements

Progress visibility cannot exceed visibility of its source records or expose
hidden task counts/statuses. Selectors must operate on an actor-authorized
scope where results are user-specific.

## 8. Validation Rules

- Inputs use approved included/excluded statuses, weights, and null/empty rules.
- Results follow approved rounding and maximum/minimum policy.
- Empty collections and all-cancelled collections have explicitly approved
  outcomes.
- Presentation locale never changes stored/computed numeric value.

## 9. Business Rules

Decision 0011 defines the Phase 6 formulas, cancellation, empty states,
rounding, bounds, and visibility. Reports must use the same centralized
services when implemented.

## 10. Expected Migrations

- None expected for a calculation-first design.
- Only measured indexes or an explicitly approved cache/snapshot design may
  add migrations; cache invalidation and backfill must be documented.

## 11. Unit Tests

- Every approved formula with zero, one, mixed, cancelled, nested, weighted,
  boundary, rounding, and over-100 scenarios as applicable.
- Determinism and type/precision.
- Arabic/English formatting parity.

## 12. Integration Tests

- Service results from realistic PostgreSQL records.
- Project/course aggregation and authorization-safe scopes.
- Query counts and no N+1 behavior.
- Consistency across every detail page that displays progress.

## 13. Browser Tests

- Representative task/course/project progress displays match service results
  in Arabic RTL and English LTR.
- Empty/cancelled states use approved localized messages.

## 14. Security Tests

- Aggregate values do not leak restricted source records.
- Forged actor/context inputs cannot broaden calculation scope.
- Logs/errors do not disclose hidden record identifiers.

## 15. Manual Verification

- Build approved fictional scenarios and calculate expected values by hand.
- Compare detail displays in both languages.
- Inspect queries for representative volumes.
- Verify no template contains business calculation logic.

## 16. Acceptance Criteria

- One centralized service owns every approved formula available at this phase.
- Calculations exactly match approved status/cancelled/weight/rounding rules.
- Authorized pages show consistent values in Arabic and English.
- Empty/boundary cases, permissions, and performance are tested.
- No duplicate formula exists in templates, reports, or views.

## 17. Dependencies

- Completed Phase 5.
- Approved decision 0011.

## 18. Rollback Considerations

- Calculation code rolls back through Git without schema changes.
- If a cache/index is approved, rollback must preserve source data and tolerate
  mixed-version deployments.
- Formula changes after release require an explicit business change record and
  regression review of dashboards/reports.
