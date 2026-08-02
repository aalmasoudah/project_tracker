# Phase 12 Verification

Verified on 2026-07-29.

## Acceptance Criteria

- Every approved role receives a dashboard whose cards and counts are derived
  only from existing permission-scoped domain selectors.
- Project progress uses the centralized Phase 6 service. Phase 12 adds no
  business formula, status, permission, or aggregate source of truth.
- Global Arabic/English search covers visible projects, courses, tasks, and
  milestones and does not expose restricted results or counts.
- Saved filters are schema-versioned, allowlisted, private to their owner, and
  protected against cross-user open/delete and unsafe return URLs.
- Kanban uses existing Task statuses. Calendar uses approved domain dates.
  Timeline and Gantt expose no write endpoint and are explicitly read-only.
- Search length, date ranges, displayed results, and planning datasets are
  bounded. Volume coverage verifies a stable global-search query budget.
- All new content is translated and usable in Bootstrap RTL/LTR layouts,
  including the critical 390 by 844 mobile workflow.

## Migration

- `workspace.0001_initial`

The generated PostgreSQL SQL was reviewed. It creates only `SavedFilter`,
including owner/view/case-insensitive-name uniqueness, schema-version and
view-type checks, owner foreign key, and the measured lookup indexes.
Migration drift is absent and the migration applied successfully to local
PostgreSQL.

## Automated Verification

```text
python scripts/update_messages.py
  862 messages; 0 untranslated
python scripts/compile_messages.py
  Arabic catalog compiled
ruff format apps config tests
  clean after formatting
ruff check .
  all checks passed
mypy apps config
  143 source files; no issues
python manage.py check
  no issues
python manage.py check --deploy
  no issues with safe fictional production configuration
python manage.py makemigrations --check --dry-run
  no changes
git diff --check
  no whitespace errors
pytest -m "not browser"
  133 passed
pytest -m browser
  11 passed together; the remaining pre-existing Phase 6 workflow passed on
  its isolated rerun after one navbar timing failure
```

Focused Phase 12 tests cover all seven roles, Arabic scoped search, restricted
manager records, dashboard and Kanban count/content privacy, filter field
allowlisting and ownership, forged view/return input, duplicate filter names,
read-only POST rejection, excessive/reversed ranges, bounded query count with
35 matching projects, and mobile Arabic-to-English direction switching.

## Manual and Browser Verification

- The dashboard, global search, saved-filter list, Kanban, calendar, timeline,
  and Gantt rendered through real Chromium.
- At 390 by 844, Arabic used RTL assets and Arabic operational labels; language
  switching produced English LTR output.
- Kanban, timeline, Gantt, and calendar offered navigation/filter controls but
  no planning mutation control.
- Mixed-direction codes and dates are isolated with `bdi`; long board content
  remains horizontally contained instead of widening the page.

## Security and Operational Review

- Existing selectors are the authorization boundary for records and
  aggregates; role names affect labels only.
- Every saved-filter lookup includes the authenticated owner and returns 404
  for a different owner.
- Only allowlisted fields are serialized. External post-action redirects are
  rejected.
- User labels are escaped by Django templates. Search is normalized using the
  existing conservative Arabic search keys without modifying stored text.
- Views cap query strings, date windows, result lists, and planning datasets;
  no cache introduces actor-crossing state.

## Limitations and Rollback

- Saved-filter sharing, editable planning views, reports/exports, and public
  search APIs remain unimplemented because they are outside Phase 12.
- Gantt and timeline are table-based read-only operational views; richer
  interactive editing requires a later explicit approval.
- Rollback may remove Phase 12 routes/templates without changing source domain
  records. Preserve user saved filters before reversing the workspace
  migration in any environment containing real use.

Recommended commit message:

`feat: complete phase 12 dashboards search and operational views`
