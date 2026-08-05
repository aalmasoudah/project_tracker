# Insight Projects / إنسايت بروجكتس

Internal project, course, task, trainee-attendance, and completion-tracking
system.

## Current Status

Phases 1 through 18 are implemented and verified locally. Phase 18 adds the
provider-neutral, non-root container and secure staging contract. Phase 17 adds a
permission-scoped project-recovery agent with dynamic allowlisted reads,
reviewed memory, cited proposals, mandatory human approval, transactional
idempotent execution, and final verification. Phase 16 remains the fixed,
CEO-only Arabic Telegram/n8n reporting channel. Live Groq/n8n activation still
requires the documented staging credentials and security UAT.

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

For local deterministic AI briefing tests, set
`AI_BRIEFING_ENABLED=true` and `AI_BRIEFING_PROVIDER=fake`. For approved live
generation, use `AI_BRIEFING_PROVIDER=groq`, keep the default
`openai/gpt-oss-120b` model, and provide `GROQ_API_KEY` only through the local
ignored `.env` or the deployment secret manager. See
`docs/RUNBOOKS/PHASE_15_AI_BRIEFINGS.md`.

The Phase 16 Telegram integration remains disabled until Django and n8n are
configured with matching secret-manager values and a native n8n Telegram
credential. Import `deploy/n8n/insight_ceo_telegram_reports.json` only into a
dedicated staging project first and follow
`docs/RUNBOOKS/PHASE_16_CEO_TELEGRAM_N8N.md`.

For local deterministic Phase 17 testing, set
`PROJECT_AGENT_ENABLED=true` and `PROJECT_AGENT_PROVIDER=fake`. Production
requires the Groq provider and defaults to `openai/gpt-oss-120b`; the 20B
model is an explicit lower-cost choice. The optional reviewed-event n8n
workflow remains disabled until its matching HMAC secrets and staging human
checkpoint are verified. See `docs/RUNBOOKS/PHASE_17_PROJECT_AGENT.md`.

For staging, build the repository `Dockerfile`, store the variables listed in
`deploy/staging/staging.env.example` in the selected platform secret manager,
and follow `docs/RUNBOOKS/PHASE_18_STAGING_DEPLOYMENT.md`. The repository does
not contain or load staging credentials.

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
