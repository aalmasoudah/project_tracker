# Phase 13: Reports and Exports

Status: Draft; blocked by report list, authorization, branding, localization,
date, and privacy decisions.

## 1. Goal

Generate only approved PDF and Excel reports using centralized business
calculations, strict authorization, validated filters, and production-quality
Arabic RTL/English LTR rendering.

## 2. Included Features

- Approved subset of project progress, overdue-task, individual attendance,
  course attendance, and project attendance summary reports.
- PDF and Excel formats exactly as approved per report.
- Fixed approved branding and metadata.
- Date-range/filter validation and empty/large dataset behavior.
- Embedded Arabic-capable fonts, correct shaping/bidi/RTL layout, localized
  headers/values, and safe bilingual content.

## 3. Excluded Features

- Unapproved ad hoc report builder, scheduled delivery, public links, or
  dashboards.
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
- Optional report request/audit metadata if approved; generated output is not
  a second system of record.

## 6. Pages Involved

- Approved report index, filter form, generate/download response, and safe
  error/empty states.
- Operational generation history only if approved.

## 7. Permission Requirements

Each report has explicit view/export permissions and actor-scoped selectors.
Personal attendance, budgets, files, and cross-department/project data require
separate approval. Possessing a generated URL must not bypass authorization.

## 8. Validation Rules

- Report type, format, date range, filters, maximum size, and locale are
  allowlisted.
- Filenames and spreadsheet cells are safe; formula injection is neutralized.
- PDF fonts are embedded/licensed and Arabic shaping/bidi is verified.
- Numbers/dates/currencies use approved locale policy without changing source
  numeric values.
- Large generation behavior is approved before introducing background jobs.

## 9. Business Rules

- Reports use centralized progress calculations.
- Only approved reports/fields/filters exist.
- Resolve report authorization, `BR-03` through `BR-07`, `BR-14`, `BR-15`,
  `RBAC-06`/`RBAC-07`, branding, Arabic terminology, calendar/digits, and
  retention.

## 10. Expected Migrations

- None for synchronous stateless generation.
- Report request/audit/output metadata migrations only if approved, with
  retention/indexes documented.

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
- Approved report catalog, fields, formats, branding assets, date/number/
  currency policy, export rights, size/background behavior, and retention.
- Approved Arabic terminology and font/branding review.

## 18. Rollback Considerations

- Generated files are disposable outputs unless retention is approved; do not
  delete retained audit metadata without policy.
- Template rollback must remain compatible with source selectors.
- Remove temporary output safely and never leave report data in public/local
  production paths.
