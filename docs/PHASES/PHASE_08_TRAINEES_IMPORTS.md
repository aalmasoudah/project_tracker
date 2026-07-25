# Phase 8: Trainees and Imports

Status: Draft; blocked by trainee identity, import, privacy, and permission
decisions.

## 1. Goal

Implement authorized trainee management and safe CSV/Excel preview-confirm
imports with explicit valid, warning, duplicate, and error outcomes.

## 2. Included Features

- Approved trainee fields and manual lifecycle.
- Course enrollment association as approved.
- CSV and Excel upload validation.
- Non-committing preview with row-level valid/warning/duplicate/error status.
- Explicit confirm/cancel and transactional write.
- Import batch/history/audit and safe failure recovery.
- UTF-8 Arabic content, approved Arabic header aliases, RTL preview, and
  localized errors.

## 3. Excluded Features

- Sessions, trainer links, attendance, notifications, and reports.
- Silent import, direct write before preview, guessed duplicates, or
  unapproved partial-import behavior.
- Real company/personal data in tests or staging.

## 4. User Stories

- As an authorized coordinator, I can add and maintain a trainee.
- As an authorized importer, I can upload, review, correct, and confirm a
  trainee file before any data is committed.
- As a privacy-limited user, I see only approved trainee fields.
- As an Arabic-speaking importer, I can use Arabic values/approved headers and
  understand every preview error in RTL.

## 5. Models Involved

- `trainees.Trainee`, approved course enrollment model.
- `ImportBatch` and `ImportRow` with safe source metadata and validation state.
- File metadata and audit events.

## 6. Pages Involved

- Trainee list/filter, create, detail, edit, archive/restore.
- Import upload, mapping if approved, preview, confirm/cancel, result/history.

## 7. Permission Requirements

The matrix must cover trainee personal fields, course scope, import/confirm,
export (if any), archive/restore, and import history. Upload permission does
not automatically grant confirmation or broad personal-data visibility.

## 8. Validation Rules

- File size, extension, detected/declared MIME, encoding, workbook structure,
  sheet, header, row count, cell type, and required values are bounded.
- Formulas/macros/external links are rejected or safely ignored according to
  approved policy.
- Duplicate identity uses approved `BR-11` and `L10N-04`.
- Arabic source text is preserved; CSV encoding failures are explicit.
- Confirm detects stale/changed preview and applies approved all-or-partial
  behavior in one transaction.

## 9. Business Rules

- Preview never commits trainee records.
- Confirm is transactional and audited.
- Resolve `BR-11`, `BR-14`, `BR-16`, import column/partial behavior, privacy,
  permissions, and Arabic normalization/header terminology.

## 10. Expected Migrations

- Initial trainee, enrollment, import batch, and import row models.
- Approved unique/check constraints and indexes for identity, course, archive,
  batch, and validation state.

## 11. Unit Tests

- Manual trainee form.
- CSV/Excel parser boundaries and row validation.
- Duplicate classification, Arabic normalization, header mapping, and
  localized messages.
- Confirm service idempotency/staleness.

## 12. Integration Tests

- Valid, warning, duplicate, invalid, empty, malformed, oversized, and mixed
  imports.
- Preview has no trainee writes; confirm transaction/audit is correct.
- Permission and course-scope isolation.
- Arabic/English data round-trip and list query counts.

## 13. Browser Tests

- Upload, preview, cancel, correct, re-upload, and confirm an English file.
- Repeat critical preview/confirm with Arabic Excel/UTF-8 CSV in RTL.
- Verify localized row errors and no write before confirmation.

## 14. Security Tests

- Malicious filenames/content types, oversized/decompression-heavy workbooks,
  formulas/external references, unauthorized history/confirm, and direct file
  access.
- Personal-data leakage through errors, logs, previews, and cross-course URLs.

## 15. Manual Verification

- Enter fictional English and Arabic trainees manually.
- Exercise every preview classification and confirmed policy.
- Inspect audit/import history, privacy boundaries, RTL tables, long names,
  and mixed-direction identifiers.

## 16. Acceptance Criteria

- Manual trainee lifecycle follows approved permissions and identity rules.
- Imports validate without writes, preview every outcome, and commit only on
  authorized confirmation using approved transactional behavior.
- Duplicate and Arabic normalization rules match approved policy.
- Personal data and uploaded files are protected.
- Arabic/English import and trainee workflows pass localization verification.

## 17. Dependencies

- Completed Phase 4 and Phase 2 authorization.
- Approved trainee schema/identity, duplicates, columns/header aliases,
  partial-import behavior, privacy, files, archive, and permission rules.
- Approved Arabic import terminology and normalization.

## 18. Rollback Considerations

- Preserve import evidence and trainee audit history.
- A failed confirm rolls back all writes according to approved atomicity.
- Parser changes must keep old batch history readable; stored source files are
  retained/deleted only under approved retention policy.
