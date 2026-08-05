# Phase 18 Verification

Date: 2026-08-06

Status: Completed and verified locally.

## Completed Criteria

| Criterion | Evidence | Result |
| --- | --- | --- |
| Immutable application image | Python and uv base images use pinned digests; application dependencies use `uv.lock`. | Passed |
| Non-root runtime | Image inspection returned user `insight`. | Passed |
| Built localization/static assets | Image contains the Arabic message catalog, Noto Sans Arabic font, and WhiteNoise `staticfiles.json` manifest. | Passed |
| Web/background topology | Provider-neutral Compose defines web, worker, and exactly one scheduler using the same image. | Passed |
| Secret isolation | Common and worker-only environment contracts are separate; only the worker receives `GROQ_API_KEY`. | Passed |
| Build-context isolation | Git, local CLI/auth state, secret files, caches, generated Celery Beat schedules, reports, uploads, and test output are excluded from the image context. Sentinel files confirmed the exclusions. | Passed |
| Secure staging settings | Staging uses the same fail-closed PostgreSQL, Redis, SMTP, S3, HTTPS, and cookie controls as production. | Passed |
| Proxy/health behavior | Proxy trust is opt-in; only the public minimal health probe is redirect-exempt. | Passed |
| No automatic migration | Image startup runs Gunicorn only; migrations remain an explicit release command. | Passed |
| Arabic/English regression | All 16 direction-aware critical browser workflows passed. | Passed |
| No schema drift | `makemigrations --check` reported no changes. | Passed |

## Executed Verification

- Translation compilation: passed.
- Ruff formatting and lint: passed; 356 files formatted, no lint errors.
- mypy strict type check: passed on 287 source files.
- Django system check: passed with zero issues.
- Migration drift check: passed; no changes detected.
- Unit, integration, and security tests: 206 passed.
- Chrome/Playwright critical workflows: 16 passed.
- Docker build: passed from a secret-free context.
- Docker exclusion sentinels: local CLI state and Celery Beat schedule files were
  absent from the final image.
- Compose staging configuration validation: passed.
- Runtime smoke: container became healthy against local PostgreSQL, returned
  only `{"database":"ok","status":"ok"}`, and rendered Arabic login as RTL.
- Secret scan: no Groq-key-shaped value was found outside the ignored local
  secret file.

One combined local gate initially exceeded its 120-second command wrapper while
tests were still green. The test suite was rerun separately with enough time and
completed successfully; this was not counted as a passing test attempt.

On the 2026-08-06 release rerun, Playwright's newly expected bundled Chromium
was not installed, so the first browser invocation failed before reaching the
application. The same 16 workflows were rerun against the installed Google
Chrome executable and all passed. This environment failure is not counted as a
passing browser attempt.

## Changed Areas

- Container: `Dockerfile`, `.dockerignore`.
- Secure settings: build, deployment, staging, and production modules.
- Deployment examples: staging common/worker environments and service topology.
- Automation: CI container build and asset/non-root checks.
- Tests: production/staging fail-closed and process-secret behavior.
- Documentation: phase specification, ADR, deployment plan, and staging runbook.

## Migrations

None.

## Security Review

- No credential or populated deployment environment is tracked.
- Staging and production retain separate settings labels and external resources.
- Web, scheduler, release, and n8n processes do not receive the Groq key.
- The health endpoint remains minimal and does not expose topology or secrets.
- Reverse-proxy trust remains disabled unless an operator explicitly enables it
  after verifying header sanitization.

## Remaining External Work

No application-code criterion remains. Real staging still needs owner-approved
provider/region, domains, billing, PostgreSQL, Redis, S3, SMTP, monitoring,
secret-manager values, and named operational contacts. Groq, n8n, and Telegram
stay disabled until the core staging gate and their separate UAT runbooks pass.

## Recommended Commit Message

`feat: add provider-neutral deployment runtime`
