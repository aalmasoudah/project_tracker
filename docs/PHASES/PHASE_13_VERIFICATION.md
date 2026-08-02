# Phase 13 Verification

Verified on 2026-07-30.

## Acceptance Criteria

- Only the four approved reports and their approved formats are available.
- Explicit export permissions match the approved seven-role matrix, and every
  data query is constrained by existing domain selectors.
- Project progress uses the centralized Phase 6 service.
- Attendance exports contain approved aggregates only and do not include
  personal attendance records or trainee identity/contact data.
- PDF and Excel output is generated in memory, capped at 5,000 rows, returned
  with private no-store headers, and not retained.
- Arabic and English output contains Gregorian/Umm al-Qura Hijri dates with
  Western digits.
- Arabic PDFs have embedded Noto Sans Arabic, shaped text, natural RTL column
  order, repeated headers, page numbers, and approved logo branding.
- Arabic Excel is RTL, styled with the approved palette, filterable, frozen,
  formula-safe, and branded. English remains LTR.
- The application theme uses the owner-supplied logo and its deep-green,
  sage, and warm-stone palette across desktop and mobile.

## Migrations

- `reports.0001_initial`
- `reports.0002_seed_phase13_permissions`

The migrations create no report data table. They define the unmanaged
permission-owning model and seed only the approved export permission matrix.
Migration drift is absent, and both migrations applied successfully to local
PostgreSQL.

## Automated Verification

```text
python scripts/update_messages.py
  896 messages; 0 untranslated
python scripts/compile_messages.py
  Arabic catalog compiled
ruff format apps config tests scripts
  clean after formatting
ruff check .
  all checks passed
mypy apps config
  154 source files; no issues
python manage.py check
  no issues
python manage.py check --deploy
  no issues with safe fictional production configuration
python manage.py makemigrations --check --dry-run
  no changes
python manage.py collectstatic --noinput
  production static collection passed
pytest -m "not browser"
  146 passed
pytest -m browser
  13 passed together
```

Focused Phase 13 coverage verifies Hijri/Gregorian formatting, Western digits,
formula-prefix neutralization, RTL Excel direction and branding, embedded-font
PDF creation, exact role permissions, denied roles, format allowlisting,
forged hidden object IDs, manager scope, no-store responses, aggregate-only
attendance privacy, PDF and Excel downloads, and mobile Arabic-to-English
direction switching.

## Visual and Manual Verification

- The supplied logo PDF was rendered and visually inspected before deriving
  the full-lockup and mark assets.
- Arabic multi-page attendance, English multi-page progress, and Arabic empty
  PDF samples were rendered through Poppler and every page was inspected.
- Visual review caught and corrected the initial Arabic title-column width and
  PDF logical-column order. The final pass showed correct shaping, natural RTL
  order, repeated headers, page numbers, branding, and no clipping.
- The report page was reviewed in the in-app browser and real Chrome at
  390 by 844. Arabic was RTL, English was LTR, the logo and palette rendered
  correctly, and no horizontal overflow occurred.
- Excel structures were reopened with OpenPyXL to verify the embedded logo,
  RTL sheet setting, theme fill, frozen header, filters, and neutralized cells.

## Security and Operations

- Server-side form choices allowlist report type, output format, locale,
  project/course object, and date range.
- Object choices are selector-backed, so forged inaccessible IDs fail
  validation without revealing records.
- Attendance reports query only approved submissions and expose aggregate
  counts.
- Fixed ASCII filenames prevent header injection; formula-like cell text is
  prefixed safely.
- Output stays in memory and responses include `Cache-Control: no-store,
  private`, `X-Content-Type-Options: nosniff`, and a sandbox policy.
- Temporary PDF renders and generated static output were removed after
  verification. The temporary visual-review account could not be deleted
  because its login audit is protected; it was deactivated, stripped of
  permissions, and assigned an unusable password.

## Limitations and Rollback

- Individual attendance, ad hoc reports, scheduling, public links, background
  generation, retained report history, and configurable branding remain
  excluded.
- Hijri conversion follows the supported Umm al-Qura dataset range; dates
  outside it receive a localized safe fallback instead of failing generation.
- Reversing the permission seed removes only Phase 13 export grants. Removing
  the routes/templates/renderers does not affect domain data because no output
  is retained.

Recommended commit message:

`feat: complete phase 13 branded bilingual reports`
