# Design System Plan

## Status and Principles

Status: Planning baseline.

The initial interface uses Django templates, Bootstrap 5, and HTMX. It should
feel consistent, accessible, responsive, and dependable for dense internal
workflows without creating a separate frontend application.

## Page Shell

- Semantic document structure with skip link, header, primary navigation,
  breadcrumb region, main content, and footer.
- Role-aware navigation is convenience only; server authorization remains
  authoritative.
- A constrained content width for forms and a wider layout for operational
  tables, boards, calendars, and reports.
- Consistent page title, supporting description, primary action, and
  contextual secondary actions.
- Development/staging environment indicators that never expose secrets.

## Core Components

- Page headers and breadcrumb trails.
- Accessible form groups, required indicators, help text, and field/non-field
  error summaries.
- Tables with captions or accessible labels, sorting/filter affordances,
  pagination, empty states, and responsive overflow.
- Cards for dashboard summaries without encoding meaning by color alone.
- Status badges whose labels come only from approved domain statuses.
- Alerts, toasts where appropriate, confirmation panels, and durable inline
  validation.
- Tabs, accordions, and modal dialogs only when keyboard/focus behavior is
  correct and content is still understandable without them.
- Approval queues, timelines, Kanban columns, calendars, and Gantt views in
  their approved later phases.

## Forms and Actions

- Use Django forms as the validation source.
- Place a clear primary action first and keep destructive/archive actions
  visually distinct.
- Preserve submitted values after validation errors.
- Display field errors near fields and a summary linked to invalid inputs.
- Require explicit confirmation and permission recheck for archive, restore,
  correction, rejection, and other consequential actions.
- Prevent duplicate HTMX submissions with server-side idempotency where the
  workflow requires it; disabled buttons alone are not sufficient.

## HTMX Conventions

- Full-page URLs remain navigable and return complete pages by default.
- HTMX requests may return bounded fragments with the same server validation
  and authorization.
- State-changing requests include CSRF protection and use approved HTTP
  methods.
- Define loading, success, validation-error, authorization-error, and network
  failure states.
- Manage focus after fragment replacement and announce meaningful updates to
  assistive technology.
- Avoid hiding required application state exclusively in the browser.

## Accessibility

- Target WCAG 2.2 AA practices for contrast, focus, labels, structure, and
  keyboard interaction.
- Use visible focus indicators and logical tab order.
- Do not rely on color, icons, position, or animation alone to communicate
  meaning.
- Associate every form control with a label and every validation message with
  the affected control.
- Provide text alternatives for meaningful images and accessible names for
  icon-only actions.
- Respect reduced motion and common browser zoom levels.
- Include automated checks where useful and manual keyboard/screen-reader
  review for critical workflows.

## Language, RTL, Dates, and Numbers

- Arabic (`ar`) and English (`en`) are first-class languages from Phase 1.
- Every user-facing literal uses Django localization; string concatenation and
  untranslated status codes are not user interface text.
- The root element sets `lang` and `dir` from the active language. Layout,
  spacing, icons, breadcrumbs, tables, forms, pagination, modals, and HTMX
  fragments must work in both RTL and LTR.
- Use logical CSS properties and Bootstrap's compatible RTL build rather than
  maintaining unrelated duplicate layouts.
- Mixed Arabic/English content must render correctly. Emails, URLs, codes,
  dates, and other LTR fragments use bounded direction isolation inside RTL
  pages.
- Use a locally served Arabic-capable font stack with clear Arabic glyphs and
  no production dependency on a public font CDN.
- Language switching is reachable by keyboard and preserves only safe local
  return URLs.
- PDF and spreadsheet Arabic/RTL requirements are implemented and visually
  verified in Phase 13.
- Default language, persisted preferences, official terminology, calendar,
  digit style, date/time display, overdue boundaries, currencies, and rounding
  remain open decisions and must not be embedded early.

## Visual Tokens

Bootstrap variables are the starting token system. Phase 1 establishes a small
application stylesheet for:

- Brand-neutral primary, surface, border, text, success, warning, and danger
  roles.
- Spacing and content-width conventions.
- Focus outline and validation states.
- Table and form density.

Company branding, logos, and final colors require supplied approved assets.
No placeholder brand should become a permanent product identity.

## Required States

Every user-facing feature considers:

- Loading.
- Empty.
- Populated.
- Filtered with no matches.
- Validation error.
- Permission denied or unavailable.
- Archived/read-only.
- Success confirmation.
- Recoverable service failure.

## Browser Coverage

Critical workflows use Playwright in Arabic RTL and English LTR with viewport,
keyboard, validation, direction, and permission assertions. Visual inspection
is required for mixed-direction content, complex tables, Arabic/RTL reports,
common Chrome zoom levels, and responsive layouts.
