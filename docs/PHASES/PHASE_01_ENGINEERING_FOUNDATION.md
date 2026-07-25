# Phase 1: Engineering Foundation

Status: Completed and verified on 2026-07-23.

## 1. Goal

Create a secure, testable Django 5.2/Python 3.13 foundation that uses
PostgreSQL in development and tests, has the custom user model in the initial
migration, renders an authenticated base page, exposes a safe health endpoint,
and passes the initial quality gate.

## 2. Included Features

- Django project and `accounts` app with custom user model.
- Split base, development, testing, and production settings.
- Environment-based configuration with safe examples.
- PostgreSQL-only development and test configuration.
- Development PostgreSQL service configuration.
- Base template, authenticated home page, Bootstrap 5, and HTMX.
- Arabic/English localization, RTL/LTR base layouts, local Arabic-capable
  fonts/assets, language switching, and compiled message catalogs.
- Minimal Django admin support needed to create/authenticate a bootstrap user.
- `/health/` application/database probe.
- Structured, secret-safe logging.
- pytest/pytest-django, Ruff, mypy, Playwright scaffolding, and CI.
- Initial documentation, ignore rules, and dependency lock.

## 3. Excluded Features

- Departments, groups/role seeding, profile fields, account lifecycle pages,
  and user-facing login/logout UI.
- Projects, courses, tasks, progress, approvals, trainees, attendance,
  notifications, reports, uploads, and audit features.
- Celery, Redis, email delivery, object-storage integration, and production
  cloud resources.
- Any unresolved business statuses, formulas, or permissions.
- A fixed default language, persisted user preference, unapproved Arabic
  business terminology, or unapproved calendar/digit policy.

## 4. User Stories

- As a developer, I can configure a PostgreSQL database and start the app with
  documented commands.
- As an authenticated bootstrap user, I can open the base home page.
- As an operator, I can probe `/health/` and distinguish healthy from database
  unavailable without seeing sensitive configuration.
- As a contributor, I can run the same quality checks that CI runs.
- As an Arabic-speaking user, I can open the foundation page in Arabic with a
  correctly mirrored RTL layout and switch safely to English LTR.

## 5. Models Involved

- `accounts.User`, extending an appropriate Django custom-user base without
  adding Phase 2 business profile behavior.

No other application models are permitted.

## 6. Pages Involved

- `/`: authenticated base page; anonymous requests are denied or redirected
  through the standard authentication mechanism without implementing the
  Phase 2 login experience.
- `/health/`: public, minimal machine-readable health response.
- `/admin/`: Django administration restricted to staff/superusers for
  development bootstrap only.
- Language-switch endpoint using Django's safe localization mechanism.

## 7. Permission Requirements

- Home requires an active authenticated session.
- Health requires no login and exposes no secret, record count, version
  inventory, database name, or stack trace.
- Admin uses Django staff/superuser checks.
- No role or object-level business permission is introduced.

## 8. Validation Rules

- Missing/invalid database configuration fails clearly; it must not fall back
  to SQLite.
- Production settings require an external secret key, `DEBUG=False`, and
  explicit hosts/origins.
- Only supported locale codes are accepted, return URLs remain local, and
  missing translations fail the documented quality check.
- Test configuration refuses unsafe non-test database targets.
- Health reports failure with an appropriate status if a trivial database
  query fails.

## 9. Business Rules

- PostgreSQL is the system of record in all environments.
- No business-domain rule is implemented.
- The unresolved questions in `BUSINESS_RULES.md` and `USER_ROLES.md` remain
  untouched.

## 10. Expected Migrations

- Initial `accounts` migration creating the custom user model and required
  many-to-many relationships to Django auth groups/permissions.
- Standard Django app migrations are applied but not edited.

The custom user migration must exist before any later app references users.

## 11. Unit Tests

- Settings selection and safe default behavior.
- Locale selection, root direction, and safe language-switch behavior.
- Health response serialization/shape.
- Logging formatter/filter behavior, including secret redaction where added.
- Custom user creation and password hashing.

## 12. Integration Tests

- Django system checks pass with test settings and PostgreSQL.
- Initial migrations apply to an empty PostgreSQL database.
- `makemigrations --check` reports no drift.
- Authenticated home renders the base template and required static assets.
- Anonymous home access is denied/redirected.
- Health succeeds with PostgreSQL and fails safely when the database check is
  forced to fail.
- Arabic/English messages compile and localized validation stays in the active
  language.

## 13. Browser Tests

- A prepared authenticated session opens `/` in Arabic RTL and English LTR.
- Direction-appropriate Bootstrap styles, Arabic-capable font, and HTMX script
  are loaded from pinned, locally served assets.
- Language switching preserves a safe local destination and correct direction.
- `/health/` returns the documented healthy response.

No account-login browser workflow is required until Phase 2.

## 14. Security Tests

- Production settings have `DEBUG=False` and reject missing critical config.
- Health output contains no secret/database details or tracebacks.
- Passwords are hashed.
- Anonymous users cannot view the home page.
- CSRF middleware and default security middleware remain enabled.
- Unsafe language return URLs and direction-spoofing content are handled
  safely.

## 15. Manual Verification

1. Recreate/install the Python 3.13 environment from locked dependencies.
2. Start the documented PostgreSQL service.
3. Apply migrations to an empty database.
4. Create a local bootstrap superuser without storing credentials in Git.
5. Authenticate through the restricted development/admin path and open `/`.
6. Open `/health/` with the database available.
7. Stop/unavailable the database and confirm a safe unhealthy response.
8. Compare development and production settings for debug/security separation.
9. Inspect Arabic RTL and English LTR layouts at common viewport/zoom sizes,
   including mixed Arabic/English text and keyboard focus.

## 16. Acceptance Criteria

- Application starts locally using PostgreSQL, never SQLite.
- Custom user model exists in the first application migration.
- Development, testing, and production settings are separate.
- Active authenticated users can render a base Bootstrap/HTMX page.
- The page and validation render in Arabic RTL and English LTR, translations
  compile, mixed-direction text remains readable, and the language switch is
  accessible and safe.
- `/health/` reports application/database health without leaking secrets.
- Structured logging is configured.
- CI and documented local commands run Ruff format/lint, mypy, pytest,
  migration drift check, Django checks, and the required Playwright smoke test.
- All required checks execute successfully.
- No business-domain features are present.

## 17. Dependencies

- Approved scope and this phase specification.
- Python 3.13, Docker/Compose or another approved local PostgreSQL service,
  and Git.
- Resolved/recreated local virtual environment; current shell does not expose
  `python` or `psql` on `PATH`.

The default language remains configurable pending `L10N-01`; generic
foundation translations must be reviewed, while business terminology is
deferred. No unresolved domain rule blocks the technical localization
foundation.

## 18. Rollback Considerations

- Before any later phase depends on the custom user migration, Phase 1 may be
  rolled back by removing the new application and recreating the disposable
  development/test databases.
- Do not rewrite the initial user migration after later migrations are shared
  or deployed.
- Dependency/tool configuration changes are reverted through Git; secrets and
  local databases are not committed.
