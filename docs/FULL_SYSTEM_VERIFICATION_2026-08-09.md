# Full System Verification — 2026-08-09

## Outcome

The current local Insight Tracker build passed the repository quality gate and
the complete automated application suite. Manual browser checks also covered
the main Arabic mobile and desktop journeys for the CEO, a KAU project manager,
a KAU supervisor, and a temporary technical-administration role.

No business rule, progress formula, approval transition, or record-visibility
rule was changed during this audit.

## Defects Found and Corrected

1. The two imported n8n workflows existed but were inactive. They were
   published, and the launcher now verifies both required workflow IDs.
2. The Arabic mobile off-canvas menu appeared below the sticky top bar. The
   panel and backdrop stacking order was corrected, visually inspected at
   390 by 844, and protected by a browser assertion.
3. The reviewed-agent n8n workflow lacked its local HMAC integration values.
   The launcher now generates a separate random local secret, retains it only
   in ignored `tmp/runtime/`, synchronizes it into n8n and the Django/Celery
   child processes, and never prints it.

The older mobile browser tests were updated to switch language from the visible
top bar instead of attempting to click through an open modal backdrop.

## Automated Quality Gate

- `ruff format --check .`: passed for 367 files.
- `ruff check .`: passed.
- `mypy .`: passed for 294 source files.
- `python manage.py check`: passed with zero issues.
- `python manage.py makemigrations --check --dry-run`: no model drift.
- `pytest -m "not browser" -q`: 242 passed.
- `pytest -m browser -q`: 17 passed using installed Google Chrome.
- `git diff --check`: passed; only Windows line-ending notices were reported.

## Functional Coverage

The automated suites cover accounts, roles, localization, security, projects,
courses, tasks, progress, approvals, trainees, attendance and review,
notifications, workspace views, reports and exports, audit/operations,
AI briefings, Telegram integration, project agents, and the Phase 20 UI.

Manual route and permission checks confirmed:

- CEO: dashboard, projects, courses, tasks, milestones, accounts, departments,
  trainees, attendance, Kanban, calendar, timeline, Gantt, saved filters,
  approvals, reports, audit, notifications, search, profile, AI briefing, and
  project-agent pages loaded without server errors.
- KAU project manager: KAU projects, task creation, courses, attendance-session
  creation, approvals, reports, and the scoped directory were available;
  another university project returned 404 and audit access was denied.
- KAU supervisor: approvals, attendance reviews, KAU tasks/projects, and scoped
  reports were available; another university project and audit were denied.
- Technical administrator: accounts, departments, audit, operations, and
  archives were available; projects, reports, and attendance were denied.

The temporary passwords and temporary role used for manual browser testing
were restored to their original hashes and groups after the test.

## Reports

The real KAU demo overdue-task export returned HTTP 200 in both formats:

- XLSX: valid ZIP/XLSX signature with 5 non-empty data rows.
- PDF: valid `%PDF-` signature and non-empty 2.69 MB output.

The browser suite also downloaded Arabic overdue-task PDF/XLSX and project
progress XLSX files with the expected filenames.

## Runtime and Integrations

- PostgreSQL and Redis: healthy.
- Django `/health/`: HTTP 200 with database status `ok`.
- Celery worker: responded `pong`; Celery Beat dispatched scheduled tasks.
- n8n `/healthz`: HTTP 200.
- Telegram and reviewed-agent workflows: active.
- Project-agent unsigned claim/callback requests: rejected with HTTP 401.
- Reviewed-agent workflow: successfully claimed a reviewed event and paused at
  the required human checkpoint without configuration or signature errors.
- Cloudflare quick tunnel: recovered from transient QUIC timeouts and
  registered a new connection; the launcher completed with exit code 0.
- Local-network health responded with HTTP 200 on the detected LAN/hotspot
  interfaces while Django listened on `0.0.0.0:8000`.

## Live External Verification

- A fresh production-shaped AI briefing was generated through Celery and the
  configured Groq `openai/gpt-oss-120b` provider. It completed in 4.738
  seconds with 10 cited evidence records, 1,700 input tokens, 1,838 output
  tokens, and a locally validated structured result.
- A real message from the owner's Telegram account traversed Telegram,
  Cloudflare HTTPS, the restricted webhook proxy, n8n, Django, Celery, Groq,
  and the Telegram response workflow. The English assistant answer completed
  successfully with a 732-character cited response, using 1,200 input tokens
  and 537 output tokens on `openai/gpt-oss-120b`.
- Fresh `/tasks`, `/overdue`, and `/attendance` Telegram requests all completed
  successfully and produced downloadable PDF document payloads. `/last`
  returned the completed answer without another model request, while `/help`
  was handled directly by n8n. The restricted proxy recorded HTTP 200 for
  every inbound Telegram webhook, and all three protected document downloads
  returned HTTP 200.
- The public Cloudflare HTTPS tunnel was reachable. Its root returned the
  intentional HTTP 404 from the restricted proxy instead of exposing the
  application or n8n editor.
- A ten-concurrent-client local load check completed 100 of 100 health/login
  requests successfully at approximately 206 requests per second; median
  latency was 28.28 ms and p95 latency was 162.74 ms.
- A real PostgreSQL logical backup was restored into a uniquely named isolated
  temporary database. The restored database matched 75 migrations, 7 projects,
  and 16 users; the temporary database and dump were removed afterward.

## Security and Branding Checks

- No Groq key or private key was found in tracked or publishable source files.
- The generated project-agent signing secret is under ignored `tmp/` only.
- No old `Insight Projects` / `إنسايت بروجكتس` branding was found in source
  filenames, repository text, the local database, or generated PDF/PPTX/DOCX
  text.

## Remaining Environment Boundary

No paid production/cloud environment or production S3 bucket is configured,
so provider-side database retention, production SMTP, private S3 transfer,
managed monitoring, a custom application HTTPS domain, and disaster recovery
in that provider cannot be tested locally. Their fail-closed settings and
application contracts are covered by the automated deployment tests.

The web interface was tested with installed desktop Chrome and mobile browser
emulation. The Telegram journey proves real iPhone-to-public-tunnel traffic,
but direct manipulation of the website on the owner's physical iPhone remains
a user-operated visual check.
