# Arabic and English Localization Plan

## Status and Objective

Status: Approved scope requirement. User-visible localization slices are
approved through Phase 14.

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
- Phase 3 project terminology, Gregorian date-only display, Western digits,
  and conservative project/client/category search normalization are approved
  in decision 0008.
- Phase 3 status translations are: Draft `مسودة`, Active `نشط`, On Hold
  `معلّق`, and Cancelled `ملغى`.
- Phase 3 priority translations are: Low `منخفضة`, Medium `متوسطة`, High
  `عالية`, and Critical `حرجة`.

Phase 4 terminology is Course `دورة`, Courses `الدورات`, Trainer `مدرب`,
Trainers `المدربون`, In person `حضوري`, Online `عن بُعد`, and Hybrid `هجين`.
Course schedules use Gregorian dates, Western digits, and Asia/Riyadh time.
Course and trainer search uses the approved conservative Arabic normalization
while preserving original text.

Phase 5 terminology includes Task `مهمة`, Tasks `المهام`, To Do
`قيد الانتظار`, In Progress `قيد التنفيذ`, Blocked `متعطلة`, Completed
`مكتملة`, and Tags `العلامات`. Task dates use Gregorian dates and Western
digits. Task/tag search applies the approved conservative Arabic
normalization while preserving original task names, descriptions, comments,
and tag names.

Phase 6 terminology is Progress `التقدم`, No countable work
`لا يوجد عمل قابل للاحتساب`, and Not applicable `لا ينطبق`. Arabic and English
show the same two-decimal bounded percentage with Western digits; locale
changes presentation only, never the numeric calculation.

Phase 7 terminology includes Milestone `مرحلة رئيسية`, Milestones
`المراحل الرئيسية`, Approval `موافقة`, Approvals `الموافقات`, Pending approval
`بانتظار الموافقة`, Approve `موافقة`, Reject `رفض`, and Rejection reason
`سبب الرفض`. Approval dates use Gregorian dates and Western digits. Arabic
reasons and bilingual identifiers preserve their original text and render
with direction isolation.

Phase 8 terminology includes Trainee `متدرب`, Trainees `المتدربون`, Import
`استيراد`, Preview `معاينة`, Duplicate `مكرر`, Warning `تحذير`, Skip `تخطي`,
and Update `تحديث`. Approved Arabic headers include `الاسم الكامل`,
`رقم الجوال`, and `البريد الإلكتروني`. Original values are preserved while
duplicate keys use decision 0013 normalization. Course-specific numbers use
Western digits.

Phase 9 terminology includes Session `جلسة`, Sessions `الجلسات`, Attendance
`الحضور`, Present `حاضر`, Absent `غائب`, Late `متأخر`, Excused `غائب بعذر`,
and Pending Supervisor Review `بانتظار مراجعة المشرف`. Scheduling and expiry
use Asia/Riyadh, Gregorian dates, and Western digits.

Phase 10 terminology includes Attendance Review `مراجعة الحضور`, Attendance
Reviews `مراجعات الحضور`, Approved Attendance `الحضور المعتمد`, Correct
Attendance `تصحيح الحضور`, Correction `تصحيح`, and Correction Reason
`سبب التصحيح`. Review, reopened-link, and correction dates use Asia/Riyadh,
Gregorian dates, and Western digits. Arabic reasons and names preserve their
original text.

Phase 11 terminology includes Notifications `الإشعارات`, Notification
Preferences `تفضيلات الإشعارات`, Task Assignments `إسناد المهام`, Approvals
`الموافقات`, Deadlines and Overdue `المواعيد النهائية والمهام المتأخرة`, and
Mentions `الإشارات`. Stored notification content is complete in Arabic and
English. Email uses the recipient's persisted language with RTL Arabic or LTR
English, while task reminder dates use Asia/Riyadh, Gregorian dates, and
Western digits.

Phase 14 terminology includes Audit log `سجل التدقيق`, Archive management
`إدارة الأرشيف`, Operations `العمليات`, System health `سلامة النظام`, Backup
status `حالة النسخ الاحتياطي`, Retention policy `سياسة الاحتفاظ`, and Restore
`استعادة`. Administrative timestamps use Asia/Riyadh and display Gregorian
plus Umm al-Qura Hijri dates with Western digits. Stable audit, environment,
status, and command codes remain machine-readable and are translated only for
presentation.

Separately approved extensions must resolve:

- Official Arabic translations for later statuses, workflow actions, and
  report names.
- Gregorian/Hijri display outside the approved Phase 3 through Phase 14
  screens and outputs.
- Arabic-Indic/Western digit display outside the approved Phase 3 through
  Phase 14 screens and outputs.
- Date/time, timezone, currency, and rounding conventions.
- Arabic duplicate and sorting rules outside the approved account and Phase 8
  trainee duplicate behavior.

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
