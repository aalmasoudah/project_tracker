# Phase 13: Reports and Exports

Status: Approved, implemented, and verified on 2026-07-30.

## 1. Goal

Generate only approved PDF and Excel reports using centralized business
calculations, strict authorization, validated filters, and production-quality
Arabic RTL/English LTR rendering.

## 2. Included Features

- Project-progress reports in PDF and Excel.
- Overdue-task reports in Excel.
- Course- and project-attendance summaries in PDF and Excel.
- Fixed Project Insight branding derived from the approved supplied logo.
- Date-range/filter validation and empty/large dataset behavior.
- Embedded Arabic-capable fonts, correct shaping/bidi/RTL layout, localized
  headers/values, and safe bilingual content.
- Gregorian and Umm al-Qura Hijri dates with Western digits.

## 3. Excluded Features

- Individual attendance or personal-data exports.
- Unapproved ad hoc report builder, scheduled delivery, public links,
  dashboards, or report history.
- Duplicate progress formulas or report-only business logic.
- Real data in tests/staging.

## 4. User Stories

- As an authorized user, I can generate an approved report over records I may
  view/export.
- As a privacy-limited user, I cannot infer/export restricted personal data.
- As an Arabic-speaking user, I receive a readable, correctly shaped and
  ordered Arabic report with approved terminology/branding.

## 5. Models Involved

- Existing domain models through selectors/progress services.
- An unmanaged permission-owning model; generated outputs and report requests
  are not retained as a second system of record.

## 6. Pages Involved

- Approved report index, filter form, generate/download response, and safe
  error/empty states.
- No operational generation history is retained.

## 7. Permission Requirements

Each report has an explicit export permission and actor-scoped selector.
CEO and Executive Manager may export all records already visible to them;
Project Manager may export managed records; Supervisor may export only
supervised course/project attendance summaries. Employee, Contractor, and
Technical Admin receive no report export permission. No persistent generated
URL exists.

## 8. Validation Rules

- Report type, format, date range, filters, maximum size, and locale are
  allowlisted.
- Filenames and spreadsheet cells are safe; formula injection is neutralized.
- PDF fonts are embedded/licensed and Arabic shaping/bidi is verified.
- Numbers/dates/currencies use approved locale policy without changing source
  numeric values.
- Synchronous generation is limited to 5,000 rows and a 366-day filter range.
- Spreadsheet formula prefixes are neutralized.

## 9. Business Rules

- Reports use centralized progress calculations.
- Only approved reports/fields/filters exist.
- Attendance reports expose approved aggregate counts only.
- Dates contain Gregorian and Umm al-Qura Hijri values with Western digits.
- Output is generated in memory and returned with private no-store headers.

## 10. Expected Migrations

- `reports.0001_initial` adds permission state only through an unmanaged model.
- `reports.0002_seed_phase13_permissions` seeds the approved role matrix.
- No report request, output, history, or retention table exists.

## 11. Unit Tests

- Report filters and permission policy.
- Data selection and centralized progress values.
- Locale/date/number formatting and safe filenames/cells.
- Arabic shaping/bidi/font registration helpers.

## 12. Integration Tests

- Authorization and record scope for every report/format.
- PDF structure/text metadata and Excel workbook/sheet/cell structure.
- Empty, boundary date, Arabic/mixed, and approved large datasets.
- No spreadsheet formula injection and no sensitive logs.

## 13. Browser Tests

- Generate/download each approved report with permitted and denied roles.
- Run critical report flow in Arabic RTL and English LTR.
- Validate useful localized empty/error states.

## 14. Security Tests

- Forged filters/IDs/formats/locales, direct/replayed download links,
  personal/budget leakage, filename/header injection, spreadsheet formulas,
  resource-exhaustion bounds, and temporary-file cleanup.

## 15. Manual Verification

- Generate every approved report in Arabic and English.
- Render every PDF page to images and inspect shaping, order, embedded fonts,
  branding, clipping, tables, page numbers, and mixed text.
- Open Excel outputs and inspect Arabic cells, direction, formulas, columns,
  filters, totals, and data integrity.
- Compare all values against source pages/central services.

## 16. Acceptance Criteria

- Only approved reports/formats/fields are available.
- Authorization and object scope are correct for every export.
- Numbers exactly match centralized services.
- PDFs/Excel open correctly and handle empty/large approved inputs.
- Arabic RTL shaping, fonts, order, terminology, and mixed content pass visual
  verification; English LTR remains correct.

## 17. Dependencies

- Completed progress, attendance, dashboard/search selectors, and permissions.
- Approved report catalog, fields, formats, branding assets, date/number
  policy, export rights, synchronous size bounds, and no-retention policy.
- Approved Arabic terminology and font/branding review are complete.

## 18. Rollback Considerations

- Generated files are disposable outputs and no report output is retained.
- Template rollback must remain compatible with source selectors.
- Remove temporary output safely and never leave report data in public/local
  production paths.
