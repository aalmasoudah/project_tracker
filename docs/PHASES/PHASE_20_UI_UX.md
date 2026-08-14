# Phase 20: UI/UX Navigation, Progress, and Profiles

Status: Approved for implementation on 2026-08-07.

## 1. Goal

Make the bilingual project-management interface easier to scan and navigate
while preserving every approved permission, workflow, and progress formula.

## 2. Included Features

- Permission-aware grouped sidebar, compact top bar, active navigation state,
  breadcrumbs, contextual quick actions, and three-click journey targets.
- Persistent/collapsible desktop navigation and accessible mobile off-canvas
  navigation with Arabic RTL and English LTR mirroring.
- Shared accessible button variants and states using the approved brand theme.
- Shared visible linear progress and SVG circular project-progress indicators.
- Global bilingual footer with correctly proportioned branding.
- Sidebar-bottom profile tab with avatar, name, and translated role.
- Secure self-service avatar upload, replacement, deactivation, protected
  delivery, fallback presentation, audit, and retained history.

## 3. Excluded Features

- New progress or portfolio aggregation formulas.
- Permission, approval, status-transition, or record-visibility changes.
- A separate frontend framework, public profile images, social profiles, image
  galleries, external avatar services, or CDN-hosted assets.
- Hard deletion of retained avatar files or lifecycle evidence.

## 4. Navigation Rules

- Common authorized destinations are reachable within three navigation
  interactions from the authenticated dashboard.
- Reaching an action form satisfies the navigation target; filling fields,
  submission, confirmations, and approval steps are not navigation clicks.
- Projects, task creation/assignment, overdue work, approvals, reports,
  attendance sessions, trainees, AI briefings, and project agents are covered.
- Security and business confirmation steps are never removed to reduce clicks.

## 5. Progress Rules

- Templates receive the existing bounded `ProgressResult`; they calculate no
  progress value.
- Linear indicators expose a visible track, completed fill, numeric value, and
  accessible state at 0, 1, 50, 99, and 100 percent.
- The project detail ring means canonical project progress only. Empty and not
  applicable states retain their existing Phase 6 meanings.

## 6. Avatar Rules

- The current user may upload, replace, or deactivate only their own avatar.
- Input is limited to JPEG, PNG, or WebP, at most 5 MiB and 4096 pixels on
  either axis. Decoded image verification is authoritative, not extension or
  browser MIME claims.
- The service removes metadata, normalizes orientation, crops a 512 by 512
  derivative, encodes WebP, and assigns a random storage name.
- Active-avatar uniqueness is enforced per user. Replacement and removal are
  transactional and audited. Historical records/files remain protected.
- Avatar reads require authentication and current account visibility; own
  sidebar delivery always remains available to an active signed-in user.

## 7. Expected Files and Migration

- Shared shell templates, progress include, profile template, and `app.css`.
- Small local shell JavaScript only where Bootstrap does not provide behavior.
- Account model, form, service, selector/view/URL, and audit action updates.
- `accounts.0004_phase20_user_avatar` migration.
- Pillow runtime dependency and lock update.
- Arabic catalog plus integration/browser tests.

## 8. Acceptance Criteria

- Desktop and mobile sidebar behavior is keyboard accessible, direction aware,
  responsive, and permission preserving.
- Representative common journeys meet the documented three-click targets.
- Buttons have consistent primary, secondary, neutral, destructive, disabled,
  focus, loading, and mobile touch states.
- Progress fill and remaining track are visually distinct, and the project
  ring shows the same value returned by the Phase 6 service.
- The footer, logo, profile tab, fallback avatar, long names, and translated
  roles render without clipping in Arabic or English.
- Malformed, oversized, deceptive, SVG, unauthorized, and cross-user avatar
  operations fail safely; replacement/removal retains historical evidence.
- Ruff, mypy, Django checks, migration checks, unit/integration tests, critical
  Playwright workflows, secret scan, and final diff review pass.

## 9. Feedback Gates

1. Specification and baseline review.
2. Shared shell/sidebar/button review.
3. Progress/footer review.
4. Profile/avatar review.
5. Arabic/English desktop/mobile final review before commit.
