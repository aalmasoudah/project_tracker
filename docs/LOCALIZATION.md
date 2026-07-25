# Arabic and English Localization Plan

## Status and Objective

Status: Approved scope requirement. Phase 2 account policy was approved on
2026-07-25; later output policies remain open.

Arabic and English are first-class across the full system. Arabic support
means more than translating headings: workflows, validation, content entry,
search, imports, notifications, dashboards, audit presentation, PDFs, and
spreadsheets must behave correctly with Arabic and mixed-direction data.

## Foundation

- Configure Django internationalization for `ar` and `en` in Phase 1.
- Arabic is the default language.
- Use Django translation catalogs for Python and template text.
- Set page `lang` and `dir` from the active language and preserve direction in
  HTMX fragments.
- Provide an accessible language switch using safe local redirects.
- Serve pinned Bootstrap LTR/RTL assets, HTMX, and Arabic-capable fonts locally.
- Compile message catalogs in CI and deployment builds.

## Content and Data

- PostgreSQL uses UTF-8 and stores original Arabic text without destructive
  normalization.
- Forms, model validation, errors, help text, empty states, confirmations, and
  permission denials are localized.
- Mixed Arabic/English identifiers use Unicode bidirectional isolation in
  presentation.
- Normalization used for search or duplicate matching is a separate derived
  operation and requires approval before it affects identity.
- Seeded statuses/groups use stable internal codes and translated labels, not
  language-specific database identifiers.

## Domain Coverage

- Accounts and organization: Arabic names and localized authentication/
  administration screens.
- Projects/courses/tasks: Arabic titles, descriptions, comments, filters,
  statuses, files, and validation.
- Trainee imports: UTF-8 CSV and Excel Arabic values; approved Arabic header
  aliases; RTL preview and localized row errors.
- Trainer links/attendance: complete Arabic external workflow, including
  expiry, submission, rejection, read-only, and correction messages.
- Notifications/email: localized subjects/templates selected using the
  recipient's approved language preference or configured default.
- Dashboards/search: Arabic query input, display, sorting, and approved
  normalization behavior.
- Reports/exports: embedded Arabic fonts, correct shaping/RTL order, bilingual
  branding, localized headers, and uncorrupted spreadsheet cells.
- Audit/operations: stable action codes with localized presentation; raw logs
  remain structured and machine-readable.

## Dates, Numbers, and Terminology

Approved for Phase 2:

- Arabic is the default, and internal users persist Arabic or English.
- The project owner approves official terminology.
- Phase 2 role translations are recorded in decision 0007.
- Account identity preserves original Arabic text. Derived search may ignore
  diacritics/tatweel and normalize Alef and Persian keyboard variants without
  merging `ة/ه` or `ى/ي`.

The following still require explicit owner approval in their later phases:

- Official Arabic translations for later statuses, workflow actions, and
  report names.
- Gregorian/Hijri display by screen/report.
- Arabic-Indic/Western digit display.
- Date/time, timezone, currency, and rounding conventions.
- Arabic duplicate and sorting rules outside the approved account search.

Until approved, implementation keeps these policies configurable or defers the
affected feature; it does not guess.

## Verification

- Unit tests for translation selection, pluralization, and safe direction
  helpers.
- Integration tests for localized validation and HTMX/full-page consistency.
- Playwright tests for each critical workflow in Arabic RTL and representative
  English LTR coverage.
- Round-trip tests for Arabic database content, filters, imports, exports, and
  search.
- Screenshot/manual review for layout mirroring, mixed-direction content,
  long translations, keyboard focus, responsive tables, and zoom.
- Rendered PDF page inspection and spreadsheet inspection for fonts, shaping,
  order, clipping, pagination, and data integrity.

## Definition of Done

A user-visible phase is incomplete if its Arabic text is missing/unreviewed,
the layout fails in RTL, validation falls back unexpectedly to English,
Arabic data is altered, or its critical Arabic workflow lacks verification.
