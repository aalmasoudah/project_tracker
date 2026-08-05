# Phase 18 Staging Deployment Runbook

## Purpose

Deploy Insight Projects to a fictional-data staging environment using the same
immutable image and security posture intended for production. This runbook is
provider-neutral; do not create billable resources until the project owner
approves the provider, region, plans, and data-residency position.

## Required Decisions and Access

Record before provisioning:

- hosting provider, Saudi/approved region, and account owner;
- staging application and n8n domains;
- managed PostgreSQL, Redis, private S3, SMTP, and monitoring providers;
- release operator, security contact, backup owner, and support contact;
- approved monthly budget and billing owner.

Staging must use separate credentials, database, Redis namespace, bucket,
email sender, Groq key, Telegram bot, and n8n project from production.

## Build

From a clean reviewed commit:

```powershell
docker build --pull --tag insight-projects:<commit-sha> .
docker inspect insight-projects:<commit-sha> --format '{{.Config.User}}'
```

The user must be `insight`. Push the image to the approved private registry and
record its immutable digest. Never use a mutable `latest` tag for promotion.

## Configuration

Use `deploy/staging/staging.env.example` as a variable checklist, not as a
credential file. Enter real values only into the provider secret manager.

Set `TRUST_X_FORWARDED_PROTO=true` only after verifying the reverse proxy
terminates HTTPS and strips or overwrites inbound `X-Forwarded-Proto`. Keep HSTS
at zero for staging and until production domain ownership and HTTPS behavior are
verified.

Keep all AI and bot feature flags disabled for the first application release.
Only the worker receives `GROQ_API_KEY` when those features are later enabled.
Use a worker-only secret environment based on `worker.env.example`; do not attach
it to web, scheduler, release, or n8n services.

## Release Order

1. Provision isolated managed PostgreSQL, Redis, bucket, SMTP, and monitoring.
2. Configure secrets and deploy the reviewed image without public traffic.
3. Run the one-off release command with `DEPLOYMENT_PROCESS_ROLE=release`:

   ```text
   python manage.py migrate --noinput
   ```

4. Start or update the web service and Celery workers.
5. Start exactly one Beat scheduler with its schedule file on writable temporary
   storage.
6. Attach HTTPS routing and configure `/health/` as the web health probe. This
   minimal endpoint alone is exempt from Django's HTTPS redirect so an internal
   platform probe can reach it; all user pages still require HTTPS.
7. Verify health before allowing staging users.

## Staging Acceptance

- `/health/` returns only `{"database":"ok","status":"ok"}` with HTTP 200.
- Login works over HTTPS; secure cookies are present and HTTP redirects to HTTPS.
- Arabic pages use RTL, Arabic font/logo assets load, and language switching to
  English produces LTR pages.
- A fictional upload is private and can be downloaded only by an authorized user.
- A fictional notification email is delivered through the staging sender.
- Worker processes a fictional queued notification; Beat schedules once only.
- Existing role and object-level permission browser tests pass against staging.
- Backup status is visible to the approved role and an isolated restore is tested.
- Logs and monitoring contain no secrets, report bodies, provider payloads, or
  personal data.

After the core gate passes, enable and test Groq, then Phase 17, then the
separate n8n/Telegram integration in that order using their existing runbooks.

## Rollback

Route traffic back to the previous image digest. Do not automatically roll back
database migrations. If integrity is uncertain, pause workers and releases,
preserve evidence, and follow the incident procedure in `docs/OPERATIONS.md`.
