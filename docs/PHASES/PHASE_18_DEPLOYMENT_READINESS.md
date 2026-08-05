# Phase 18: Deployment Readiness

Status: Completed and verified locally on 2026-08-05.

## 1. Goal

Make the existing application reproducibly deployable to an isolated staging
environment without choosing or purchasing a provider, domain, or paid service.

## 2. Included Features

- A locked Python 3.13 container image for the Django application.
- Non-root Gunicorn runtime with built static assets and compiled translations.
- Production-equivalent, fail-closed staging settings.
- Explicit, opt-in reverse-proxy HTTPS header trust.
- Provider-neutral web, Celery worker, and single Beat scheduler topology.
- A secret-free staging configuration contract and release checklist.
- CI validation that the production container builds.

## 3. Excluded Features

- Purchasing infrastructure, domains, email, storage, or monitoring plans.
- Selecting a region or accepting a data-residency contract.
- Deploying real company or university data to staging.
- Enabling Groq, Telegram, or n8n before their security UAT.
- Production launch, DNS cutover, or HSTS activation.

## 4. User Stories

- As an operator, I can build one immutable image and use it for web and workers.
- As an operator, I can deploy staging without storing secrets in Git.
- As a reviewer, I can verify health, Arabic/English assets, and service topology.
- As a security owner, I can see which external decisions remain unapproved.

## 5. Models Involved

None.

## 6. Pages Involved

No new page. Existing `/health/`, authentication, Arabic, and English pages are
used for deployment verification.

## 7. Permission Requirements

Existing application permissions are unchanged. Provider and secret-manager
access belongs only to the separately authorized infrastructure operator.

## 8. Validation Rules

- Staging must use `config.settings.staging` and the `staging` environment label.
- Production must use `config.settings.production` and the `production` label.
- Both require HTTPS, PostgreSQL, Redis, SMTP, and private S3 configuration.
- Forwarded-protocol headers are trusted only when explicitly enabled behind a
  proxy that removes client-supplied values.
- The image and example manifests contain no credentials.
- The Groq credential is scoped to the worker process and never supplied to
  web, Beat, release, or n8n services.

## 9. Business Rules

No business rule changes.

## 10. Expected Migrations

None.

## 11. Unit Tests

- Production settings remain fail closed.
- Staging settings use equivalent security controls and require the staging
  environment label.
- Reverse-proxy trust is disabled by default and enabled only explicitly.

## 12. Integration Tests

The existing PostgreSQL integration suite remains required.

## 13. Browser Tests

The existing critical browser suite remains required. Staging smoke testing must
also cover login, Arabic RTL, English LTR, static assets, and `/health/`.

## 14. Security Tests

- Build context excludes secrets, uploads, caches, reports, and Git history.
- Container runs as a non-root user.
- No migration runs automatically when web containers start.
- Exactly one Beat scheduler is deployed.
- Staging and production credentials and data stores remain separate.

## 15. Manual Verification

1. Build the container with no local `.env` dependency.
2. Inspect the runtime user and built Arabic catalog/font assets.
3. Validate the example Compose file with protected external configuration.
4. Run migrations as a one-off release command against a fresh staging database.
5. Start web, worker, and exactly one scheduler.
6. Verify health, login, Arabic RTL, English LTR, static assets, email, and uploads.

## 16. Acceptance Criteria

- One source image runs web, worker, scheduler, and release commands.
- Dependencies come from the lock file and the process runs non-root.
- Static assets and Arabic/English catalogs are present in the image.
- Staging configuration is secure, explicit, provider-neutral, and secret-free.
- The full repository quality gate and a clean container build pass.
- External provider, ownership, and production-launch decisions remain visible.

## 17. Dependencies

Completed Phases 1-17, Docker, managed PostgreSQL, managed Redis, private
S3-compatible storage, authenticated SMTP, and an HTTPS reverse proxy.

## 18. Rollback Considerations

Redeploy the previous immutable image. Do not reverse migrations automatically.
If health or smoke checks fail, keep the old service live, stop promotion, and
preserve logs and database state for review.
