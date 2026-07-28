# Phase 6 Verification

Verified on 2026-07-28 against PostgreSQL and Python 3.13.

## Completed Criteria

- One calculation-only `progress` application owns task, course, and project
  formulas; no percentage is editable, cached, or duplicated in templates.
- Leaf tasks use approved status values, parent tasks recursively average
  direct countable children, and cancelled/archived branches are excluded.
- Courses average top-level tasks. Projects equally average their available
  direct-task and course categories, with equal weighting inside categories.
- Empty and excluded states are explicit. Public values are bounded from
  0 through 100 and rounded to two decimals with `ROUND_HALF_UP`; internal
  values remain unrounded `Decimal` values.
- Authorized project, course, and task detail pages show the centralized
  result. Progress is withheld when the actor cannot see all source work.
- The Phase 5 hierarchy display was tightened so assigned users cannot see
  hidden parent or subtask names.
- Arabic/English labels, localized empty/excluded states, RTL/LTR direction,
  Western digits, and mobile layouts were verified.

## Migrations

No model or schema changes were made. `makemigrations --check --dry-run`
reported no changes.

## Executed Quality Gate

- `python scripts/update_messages.py`: 500 messages, 0 untranslated.
- `python scripts/compile_messages.py`: passed.
- `ruff format --check .`: passed.
- `ruff check .`: passed.
- `mypy .`: passed across 114 source files.
- `python manage.py check`: passed.
- `python manage.py check --deploy` with safe fictional production
  configuration: passed.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- `pytest -m "not browser" -q`: 68 passed, 6 deselected.
- `pytest -m browser -q`: 6 passed, 68 deselected.
- `docker compose config --quiet`: passed.
- `git diff --check`: passed.

## Browser and Manual-Equivalent Simulation

At a 390 × 844 mobile viewport, an isolated authorized Executive scenario
contained:

1. A project-task category at 50.00 percent from one completed and one To Do
   child.
2. A course category at 100.00 percent from one completed course task.
3. A project result at 75.00 percent from equal weighting of those categories.
4. An empty project and a cancelled course.

The Arabic RTL detail pages displayed `75,00%`, `100,00%`, and `50,00%`,
remained within the viewport, and showed `لا يوجد عمل قابل للاحتساب` and
`لا ينطبق` for the empty and excluded states. Switching to English changed
the document to LTR and displayed the same numeric result as `50.00%`.

The service-level query guard verified a representative project calculation
in four queries after permission caching, including its object-scope check.

## Security Review

- Actor-aware services return no progress to Employee or Contractor roles
  because their assigned-task scope can omit hierarchy and aggregation
  sources.
- Manager, Supervisor, Executive Manager, and CEO paths retain their existing
  object access; Supervisor project aggregation is withheld when a hidden
  non-active course exists.
- Assigned-user task details filter parent and child relationships through
  the same authorized task selector; direct hidden-task URLs remain 404.
- Calculations do not accept client-supplied percentages and do not expose
  record identifiers in errors rendered to users.

## Limitations and Deferred Work

- Milestone progress and project completion approval extend the engine in
  Phase 7.
- Approval- and attendance-based course components wait for their approved
  models and phases.
- Dashboards, reports, notifications, and progress caching remain deferred.

Recommended commit message:

`feat: implement phase 6 progress engine`
