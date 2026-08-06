# Fictional University Showcase Runbook

## Purpose

The development-only showcase represents three fictional client programs:

- King Abdulaziz University (KAU): university-services digital transformation.
- King Saud University (KSU): research and innovation enablement.
- King Khalid University (KKU): student-experience development.

Each program is represented by a university client and a bilingual project
category. Every program contains multiple projects. All projects belong to one
fictional Insight Projects PMO department so the approved department boundary
still permits shared analysts, quality staff, and contractors to work across
programs. University specialists remain assigned only to their program.

The dataset contains only fictional names, phone numbers, email addresses, and
business records. It is suitable for local demonstrations and must not be
promoted as production or university data.

## Coverage

The loader creates source data for accounts and roles, projects and teams,
courses and trainers, nested tasks and collaboration, progress, milestones and
sequential approvals, trainee CSV import, trainer links, attendance review and
correction, notifications, saved workspace filters, reports, audit, archives,
AI briefings, CEO Telegram reports, and project-recovery agent runs.

The generated states intentionally include active, draft, on-hold, archived,
completed, cancelled, blocked, overdue, due-tomorrow, pending approval,
approved, rejected, corrected, imported, and cancelled-import examples. AI,
Telegram, and the project agent use the same source records and remain subject
to their existing feature flags, credentials, permission checks, and human
approval boundaries.

## Safety Boundary

`load_university_showcase` is destructive. It is restricted to
`DEPLOYMENT_ENVIRONMENT=development`, requires `--apply`, and requires the exact
confirmation `LOAD-UNIVERSITY-SHOWCASE:development`.

Before using it:

1. Stop Django, Celery, n8n, and outbound tunnels.
2. Create and verify a PostgreSQL backup outside Git.
3. Back up private media when it contains files that must be recoverable.
4. Confirm that `zx` is the one active superuser to retain.

The command deletes development application records, retains the `zx` account
and its password hash, restores its Technical Admin role, and rebuilds the
fictional showcase. It does not change source code, migrations, environment
secrets, the n8n credential store, or the `zx` password.

## Load Command

Supply a temporary demonstration password at runtime; never add it to Git:

```powershell
uv run python manage.py load_university_showcase `
  --environment development `
  --demo-password "<runtime-demo-password>" `
  --apply `
  --confirm "LOAD-UNIVERSITY-SHOWCASE:development"
```

All generated internal demo accounts use the runtime password. The
`demo.new.employee` account additionally keeps the required first-login
password-change flow. The `zx` password remains unchanged.

## Demonstration Order

1. Sign in as the fictional CEO and show the Arabic dashboard.
2. Open KAU Portal to show the client/program mapping, shared team, tasks,
   progress, budget, courses, and approvals.
3. Open reports and generate overdue-task PDF and Excel outputs.
4. Open trainees and attendance to show confirmed import, cancelled preview,
   pending review, rejection/resubmission, approval, and correction evidence.
5. Generate and review an Arabic AI project briefing.
6. Start a project-recovery agent run, inspect its dynamically selected tools,
   and show that the proposal pauses for a separately authorized approver.
7. Approve one proposal as an Executive Manager, show final verification, and
   mark the run reviewed to create project memory.
8. Send `/help`, `/tasks`, `/overdue`, or `/attendance` through the bound CEO
   Telegram chat after the approved n8n workflow is active.
9. Finish with the business audit and archive center.

## Verification

Run:

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest tests/unit tests/integration -q
$env:PLAYWRIGHT_BROWSER_EXECUTABLE = "C:\Program Files\Google\Chrome\Application\chrome.exe"
uv run pytest tests/browser -q
```

The focused integration test is
`tests/integration/test_university_showcase.py`.
