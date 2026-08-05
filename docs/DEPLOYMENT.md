# Deployment Plan

## Status and Target

Status: Provider-neutral runtime implementation in Phase 18.

The first production architecture is a Dockerized Django monolith served by
Gunicorn, backed by managed PostgreSQL, with private S3-compatible storage.
The current technical recommendation is Google Cloud Dammam when Saudi data
residency is required or unresolved. Render Frankfurt remains the simpler
alternative only after non-Saudi processing is explicitly approved. Final
provider account, plans, domain, budget, and data-residency requirements must
be confirmed before infrastructure purchase. See
`docs/DEPLOYMENT_PROVIDER_EVALUATION.md`.

## Environments

| Environment | Data | Database | Storage | Purpose |
| --- | --- | --- | --- | --- |
| Development | Fictional/local | PostgreSQL | Private local development storage | Developer feedback |
| Test/CI | Generated | Ephemeral isolated PostgreSQL | Temporary test storage | Automated verification |
| Staging | Fictional or anonymized only | Separate managed PostgreSQL | Separate private bucket | UAT and release validation |
| Production | Approved company data | Separate managed PostgreSQL | Separate private bucket | Live operation |

Credentials, databases, buckets, monitoring projects, and email configuration
must not be shared between staging and production.

## Runtime Services

Phases 1 through 10:

- `web`: Gunicorn/Django.
- `db`: PostgreSQL locally; managed PostgreSQL outside local development.

From Phase 11:

- `redis`: broker and optional approved cache.
- `worker`: Celery worker.
- `scheduler`: Celery Beat or approved platform scheduler.

From Phase 16, when explicitly enabled:

- `n8n`: a separately secured HTTPS orchestration service with no database or
  Redis credential and an isolated native Telegram credential.

Migrations run as a controlled release step, never automatically in every web
container startup.

## Container Plan

- Use a supported Python 3.13 slim base image.
- Install locked dependencies.
- Copy only required source and static assets.
- Run as a non-root application user.
- Collect static files during the build.
- Compile Django message catalogs and include pinned Arabic-capable fonts and
  both direction-aware asset variants.
- Serve static assets through the selected production strategy.
- Start the web process with Gunicorn.
- Add an application health check.
- Exclude `.env`, `.git`, local virtual environments, uploads, backups, test
  artifacts, and production data through `.dockerignore`.

The Docker image must be reproducible from repository files and documented
environment variables.

## Configuration Contract

Expected variable categories include:

- Django settings module, secret key, allowed hosts, trusted origins, base URL,
  timezone configuration, supported languages, and configurable default
  language.
- PostgreSQL database URL.
- Object-storage endpoint, region, bucket, and restricted credentials.
- Redis URL after Phase 11.
- Email provider settings after Phase 11.
- Monitoring DSN and environment identifier.
- A settings module and matching environment label: `config.settings.staging`
  with `staging`, or `config.settings.production` with `production`.
- Explicit `TRUST_X_FORWARDED_PROTO=true` only when the selected HTTPS proxy
  strips or overwrites the client-supplied forwarding header.
- Phase 15 AI feature flag, approved Groq model, reasoning effort, bounded
  timeout/output/evidence/quota values, and secret-manager `GROQ_API_KEY`.
- Phase 16 feature flag, fixed CEO username/private chat ID, signing/download
  TTLs, row/quota/lease bounds, and a secret-manager signing secret shared only
  with the dedicated n8n deployment.
- Phase 17 feature/provider/model flags, step/token/time/result/quota/proposal
  bounds, secret-manager Groq key, and an optional independent n8n HMAC secret.

`.env.example` lists safe names and example formats without real credentials.
Each settings module validates required production configuration and fails
closed on missing or unsafe values.

When AI briefings are enabled in production, the provider must be `groq`, the
model must be `openai/gpt-oss-120b` or `openai/gpt-oss-20b`, and a Groq key is
required. The fixed outbound endpoint is
`https://api.groq.com/openai/v1/chat/completions`. Staging and production use
different keys. The web, worker, and scheduler processes all receive the same
non-secret AI settings; only processes that execute jobs need the provider
secret.

When Phase 16 is enabled, `APP_BASE_URL` must be a verified HTTPS origin
reachable by n8n. n8n uses an independently secured HTTPS webhook origin,
stores the Telegram bot token in its native credential store, receives the
HMAC signing secret from the deployment secret manager, allows only the
built-in `crypto` module in Code nodes, and disables successful and failed
execution-data retention. Activate the imported workflow only after the
Phase 16 staging checklist passes.

When Phase 17 is enabled in production, the provider must be `groq`; the
default model is `openai/gpt-oss-120b` and only `openai/gpt-oss-20b` is an
allowed override. Web, worker, and Beat use the same bounded settings, while
only worker processes receive the Groq secret. If the reviewed-event n8n
workflow is enabled, Django and the dedicated n8n deployment receive the same
independent 32-byte signing secret, n8n allows only built-in `crypto`, and
success/error/progress retention stays disabled. Activate after the Phase 17
staging checklist passes.

## CI/CD Flow

```text
feature branch
-> pull request
-> quality and security checks
-> human review
-> merge
-> staging build and release migration
-> health/smoke/browser verification
-> approved production promotion
-> production release migration
-> health and smoke verification
```

CI must not deploy unreviewed pull-request code to production or expose
production secrets to forked/untrusted jobs.

## Release Steps

1. Confirm required checks and approvals.
2. Verify backup/recovery readiness for migrations that need it.
3. Build one immutable image.
4. Apply reviewed migrations through the release step.
5. Start or update web/worker processes.
6. Verify `/health/` and platform health.
7. Run permission-safe smoke checks.
8. Watch errors, latency, database capacity, and worker state.
9. Record the release and rollback point.

For Phase 17, also confirm a worker processes one fictional staging run, Beat
recovers stale work and expires an aged pending proposal, approval executes
once through a currently authorized actor, and optional n8n remains inactive
until separately approved.

## Rollback

- Roll back application code by redeploying the previous known-good image.
- Prefer backward-compatible expand/migrate/contract database changes.
- Do not assume a migration is reversible; document the phase-specific path.
- Use database restoration only under an approved operational incident
  procedure, not as a routine web action.
- Pause releases when data integrity is uncertain and preserve evidence.

## Production Hardening

- `DEBUG=False`.
- HTTPS redirect and secure cookies after proxy/HTTPS verification.
- Approved hosts and CSRF trusted origins.
- Content-type sniffing protection and clickjacking protection.
- HSTS introduced carefully after domain validation.
- Private encrypted object storage with authorized, time-limited access.
- Centralized error/performance monitoring without sensitive payloads.
- Managed database backups plus documented restoration testing.

## Clean-Install Gate

Before staging and production readiness:

1. Build without developer-machine caches.
2. Create a fresh PostgreSQL database.
3. Apply all migrations.
4. Collect static files.
5. Compile translations and verify Arabic/font assets are present.
6. Run Django checks and tests inside the built environment.
7. Start the services and verify health plus Arabic/English smoke pages.
8. Tear down the test environment and confirm no hidden local dependency.
