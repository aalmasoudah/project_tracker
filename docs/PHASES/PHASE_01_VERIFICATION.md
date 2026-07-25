# Phase 1 Verification Record

Verified: 2026-07-23

Specification: `PHASE_01_ENGINEERING_FOUNDATION.md`

## Result

Phase 1 is complete. Every Phase 1 acceptance criterion passed locally, and
no Phase 2 business-domain feature was introduced.

Remote GitHub Actions was configured but was not executed from this local
workspace. Its commands match the locally executed quality gate.

## Verified Environment

- Python 3.13.13 in the project `.venv`.
- Django 5.2.16 from the locked dependency set.
- PostgreSQL 17 in Docker Compose for development and testing.
- Google Chrome with Playwright for the critical browser workflow.

The previous Python 3.14 virtual environment was preserved locally as an
ignored backup. It is not used by the project and is not tracked by Git.

## Acceptance Criteria

| Criterion | Evidence | Result |
| --- | --- | --- |
| PostgreSQL-only local application | Development, testing, and production settings reject non-PostgreSQL URLs; application and tests connected to PostgreSQL. | Passed |
| Initial custom user model | `accounts.0001_initial` creates the custom user and auth relationships before later domain apps. | Passed |
| Split settings | Base, development, testing, and production modules load independently; production fails closed. | Passed |
| Authenticated application shell | Anonymous access is denied; authenticated rendering is covered by integration and browser tests. | Passed |
| Arabic and English | Compiled Arabic messages, RTL/LTR document direction, local direction-specific Bootstrap, Arabic-capable font, safe language switching, and mixed-direction text were verified. | Passed |
| Safe health endpoint | Healthy PostgreSQL returns `200`; an unavailable database returns minimal `503` JSON in about three seconds and recovers to `200`. | Passed |
| Structured logging | JSON output and secret redaction are covered by tests. | Passed |
| Reproducible quality gate | Locked dependencies, local commands, CI workflow, Ruff, mypy, pytest, Playwright, Django checks, and migration drift checks are present. | Passed locally |
| No later-phase features | No project, course, task, attendance, progress, approval, report, or notification model was added. | Passed |

## Migration Verification

- Generated and reviewed `apps/accounts/migrations/0001_initial.py`.
- Reviewed the generated PostgreSQL SQL before application.
- Applied the custom and standard Django migrations successfully to empty
  `tracker` and `tracker_test` PostgreSQL databases.
- `python manage.py makemigrations --check` reported no model drift.

## Commands Executed

```powershell
uv sync --locked --all-groups
python scripts/compile_messages.py
ruff format --check .
ruff check .
mypy .
python manage.py check
python manage.py makemigrations --check
pytest -m "not browser"
$env:PLAYWRIGHT_BROWSER_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
pytest -m browser
docker compose config --quiet
docker compose exec -T db pg_isready -U tracker -d tracker
```

Results:

- Ruff format: 34 files already formatted.
- Ruff lint: all checks passed.
- mypy: no issues in 32 source files.
- Django system checks: no issues.
- Migration drift: no changes detected.
- Unit, integration, and security suite: 20 passed, 1 browser test deselected.
- Browser suite: 1 passed, 20 non-browser tests deselected.
- PostgreSQL: accepting connections; Compose service healthy.

## Manual and Browser Verification

- Inspected Arabic desktop and mobile layouts and English desktop layout.
- Confirmed correct `lang` and `dir`, mirrored layout behavior, readable
  mixed Arabic/English content, keyboard focus, and no clipping or overflow.
- Confirmed local Bootstrap LTR/RTL, HTMX, and Noto Sans Arabic assets loaded
  without failed requests.
- Confirmed the authenticated foundation page and language switch in a real
  Chrome browser.
- Confirmed `/health/` returned safe JSON for healthy, unavailable, and
  recovered database states without revealing connection details.

## Security Review

- No SQLite fallback exists.
- Local secrets and virtual environments are ignored.
- Production requires an external secret, explicit hosts, PostgreSQL, secure
  cookies, HTTPS redirect, and secure response headers.
- Password hashing, anonymous denial, CSRF middleware, safe redirects,
  direction-spoofing containment, and health-response redaction are tested.
- Front-end runtime assets are pinned and served locally.

## Limitations and Follow-up

- The remote GitHub Actions workflow remains to be observed on the first push.
- The user-facing login and account lifecycle intentionally remain Phase 2.
- Business Arabic terminology, calendar policy, and digit policy remain
  deferred to their documented decisions; the technical Arabic/RTL foundation
  is complete.
