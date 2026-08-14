# Phase 20 Verification

Verified on 2026-08-07.

## Outcome

Phase 20 is complete. The authenticated application now uses a bilingual,
permission-aware responsive shell with grouped navigation, a compact top bar,
breadcrumbs, a footer, consistent action buttons, accurate progress visuals,
and a protected self-service profile-picture workflow.

No progress formula, permission, approval transition, or visibility rule was
changed.

## Acceptance Evidence

- Desktop navigation is persistent and collapsible; the preference is stored
  locally in the browser. Mobile navigation uses Bootstrap off-canvas behavior.
- Arabic navigation opens from the right and English navigation opens from the
  left. Both variants avoid horizontal page overflow at the tested mobile and
  desktop viewport sizes.
- Navigation links continue to be rendered only when the current user has the
  corresponding permission.
- The current navigation destination is marked visually and with
  `aria-current`; authenticated non-dashboard pages include a breadcrumb back
  to the dashboard.
- Linear progress uses the existing bounded Phase 6 result and renders a
  visible track, fill, percentage, and accessible value. CSS values use
  unlocalized decimal separators, so Arabic values fill correctly.
- Project detail uses an SVG ring showing the same canonical project progress.
- The sidebar profile tab shows the user's avatar or fallback initial, display
  name, and localized role, and opens the profile page.
- Accepted profile pictures are verified as JPEG, PNG, or WebP; limited to 5
  MiB and 4096 pixels per axis; orientation-normalized; metadata-stripped;
  cropped to 512 by 512; and stored as a randomly named WebP derivative.
- Replacement and deactivation are transactional and audited. Historical
  avatar records and files remain retained. Avatar delivery is authenticated
  and rechecks account visibility.
- The Arabic message catalog contains 1,208 active messages and zero
  untranslated messages.

## Three-Click Journey Check

Navigation clicks are counted from the authenticated dashboard. Form input,
submission, approval confirmation, and security checkpoints are not removed or
counted as navigation clicks.

| Journey | Route | Clicks |
| --- | --- | ---: |
| Project list | Dashboard -> Projects | 1 |
| Task creation/assignment form | Dashboard -> Tasks -> Create task | 2 |
| Overdue report controls | Dashboard -> Reports | 1 |
| Approval queue | Dashboard -> Approvals | 1 |
| Attendance session creation | Dashboard -> Sessions -> Create session | 2 |
| Trainee directory | Dashboard -> Trainees | 1 |
| Project team management | Dashboard -> Projects -> Project -> Manage team | 3 |
| AI briefing request | Dashboard -> Projects -> Project -> Generate AI Briefing | 3 |
| Project agent request | Dashboard -> Projects -> Project -> Start Project Agent | 3 |

The integration suite asserts the relevant permission-scoped links and action
forms for these representative journeys.

## Database

- Added and reviewed `accounts.0004_phase20_user_avatar`.
- The migration adds the protected avatar record, active-avatar uniqueness
  constraint, active-state consistency constraint, and lookup index.
- The migration was applied successfully to the local development database.
- `manage.py makemigrations --check --dry-run` reports no model drift.

## Automated Verification

- `ruff check .`: passed.
- `mypy .`: passed for 296 source files.
- `python manage.py check`: passed with zero issues.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- `pytest -m "not browser" -q`: 242 passed, 17 deselected.
- `pytest -m browser -q`: 17 passed, 242 deselected using installed Google
  Chrome.
- Focused Phase 20 integration coverage: 10 passed.
- Focused Phase 20 browser coverage: passed in Arabic mobile and English
  desktop modes, including avatar preview/upload, RTL off-canvas navigation,
  collapse state, progress values, footer, and overflow checks.
- Repository secret scan found no Groq API key value.

## Manual Visual Verification

Playwright screenshots were rendered and inspected at:

- 390 by 844 Arabic mobile with the RTL sidebar open.
- 1440 by 900 English desktop project detail.

The logo proportions, menu grouping, fixed profile tab, button grouping,
breadcrumb, footer, progress fill, 50-percent ring, and page boundaries were
visually checked. The screenshots are temporary verification artifacts under
`tmp/phase20-visual-review/` and are not application assets.

## Security and Retention

- Upload checks trust decoded image data rather than the filename or browser
  MIME claim.
- SVG, malformed, oversized, and over-dimension uploads fail without creating
  an avatar record.
- Cross-user avatar reads outside current visibility return 404.
- Avatar files are served privately with `nosniff` and restrictive content
  security headers.
- Direct avatar deletion is protected. Removing a profile picture deactivates
  it from display while preserving the retained record and file.

## Limitations

- Profile pictures are stored using the configured Django media storage. A
  production deployment must continue to use the approved private
  S3-compatible media backend and access controls.
- The three-click rule measures navigation only; it never bypasses data entry,
  approval, authorization, or confirmation steps.

## Recommended Commit Message

`feat: add responsive navigation progress visuals and user avatars`
