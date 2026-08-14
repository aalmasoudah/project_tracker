# Decision 0025: Phase 20 UI/UX, Navigation, and Profile Avatars

Date: 2026-08-07

Status: Approved

## Decision

Phase 20 improves the existing Django template interface without changing
business calculations, object visibility, or workflow authority. Authenticated
navigation moves to a permission-aware responsive sidebar: persistent and
collapsible on desktop, off-canvas on mobile, on the left for English and the
right for Arabic. A compact top bar, contextual quick actions, breadcrumbs,
and grouped navigation make common authorized destinations reachable within
three navigation interactions from the dashboard. Login, form completion,
confirmations, and approval decisions are excluded from that navigation count.

All progress displays use the existing Phase 6 progress service. A shared
linear indicator makes the completed and remaining portions visible, while an
SVG ring presents canonical project progress. Phase 20 defines no portfolio
average and performs no progress calculation in a template.

The sidebar ends with the current user's avatar, display name, and translated
role. The profile page permits the user to upload, replace, or deactivate their
own avatar. JPEG, PNG, and WebP input is decoded and verified with Pillow,
metadata is discarded, and a bounded WebP derivative is stored under a random
name. SVG and unverified uploads are rejected. Avatar files and lifecycle
records follow the existing protected retention rule: removal hides the avatar
and restores the fallback presentation but does not hard-delete retained
historical evidence.

## Consequences

- Existing view and object permissions remain authoritative; navigation
  visibility is never treated as an authorization control.
- Phase 20 adds one protected avatar model and reviewed migration.
- Development uses private local media and deployed environments use the
  existing private S3-compatible storage.
- Avatar delivery is permission checked and does not expose storage paths.
- The visual system remains Bootstrap 5 plus small local CSS/JavaScript; no
  frontend framework or external CDN is introduced.
