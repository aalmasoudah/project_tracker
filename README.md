# Company Project Tracker

Internal project, course, task, trainee-attendance, and completion-tracking
system.

## Current Status

Phases 1 through 11 are complete. Phase 11, Notifications and Background
Jobs, was implemented and verified on 2026-07-29.

Approved scope includes first-class Arabic and English support across the UI,
validation, search, imports, notifications, operational views, PDF/Excel
reports, and RTL/LTR layouts.

## Local Setup

Requirements:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop with Docker Compose

From PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d db redis
uv sync --locked --all-groups
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

In two additional PowerShell terminals, run the local notification worker and
scheduler:

```powershell
uv run celery -A config worker --loglevel=INFO --pool=solo
uv run celery -A config beat --loglevel=INFO
```

Development email uses the console backend, so localized email content appears
in the worker terminal without contacting a real provider.

The PostgreSQL initialization script creates both `tracker` and
`tracker_test` on a fresh Docker volume. If the volume existed before Phase 1,
create `tracker_test` once with:

```powershell
docker compose exec db createdb -U tracker tracker_test
```

Open:

- User login: <http://127.0.0.1:8000/accounts/login/>
- Authenticated application: <http://127.0.0.1:8000/>
- Projects: <http://127.0.0.1:8000/projects/>
- Courses and trainers: <http://127.0.0.1:8000/courses/>
- Tasks and collaboration: <http://127.0.0.1:8000/tasks/>
- Milestones: <http://127.0.0.1:8000/approvals/milestones/>
- Approval queue: <http://127.0.0.1:8000/approvals/>
- Trainees and imports: <http://127.0.0.1:8000/trainees/>
- Sessions: <http://127.0.0.1:8000/attendance/>
- Attendance review queue: <http://127.0.0.1:8000/attendance/review/>
- Notifications: <http://127.0.0.1:8000/notifications/>
- Recovery-only Django administration: <http://127.0.0.1:8000/admin/>
- Health check: <http://127.0.0.1:8000/health/>

Create accounts and departments through the localized Phase 2 application.
The Django administration remains a restricted superuser recovery surface.

## Quality Gate

```powershell
uv sync --locked --all-groups
uv run python scripts/compile_messages.py
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run python manage.py check
uv run python manage.py makemigrations --check
uv run pytest -m "not browser"
$env:PLAYWRIGHT_BROWSER_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
uv run pytest -m browser
```

CI installs GNU gettext and additionally verifies Django's native
`compilemessages` command. Windows development uses the equivalent typed
Python compiler script so gettext does not need a system-wide installation.

## Settings

- `config.settings.development` loads local `.env`.
- `config.settings.testing` requires `TEST_DATABASE_URL` ending in `_test`.
- `config.settings.production` fails closed when the database, secret key,
  allowed hosts, HTTPS application URL, Redis broker, authenticated SMTP, or
  private S3-compatible storage credentials are missing or unsafe.
- SQLite is not configured in any environment.

## Project Documentation

Start with:

- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DATA_MODEL.md`
- `docs/SECURITY.md`
- `docs/LOCALIZATION.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/TEST_STRATEGY.md`
- `docs/DEPLOYMENT.md`
- `docs/OPERATIONS.md`

Development follows the permanent repository rules in `AGENTS.md` and proceeds
one approved phase at a time.
