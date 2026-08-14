# Decision 0023: Provider-Neutral Deployment Runtime

Date: 2026-08-05

Status: Approved

## Decision

Insight Tracker uses one locked, non-root Python 3.13 container image for the
Gunicorn web process, Celery workers, the single Celery Beat scheduler, and
one-off release commands. Migrations remain an explicit release action and are
never coupled to web startup.

Staging and production use separate settings entry points but share the same
fail-closed deployment controls. Both require PostgreSQL, Redis, authenticated
TLS SMTP, private S3-compatible storage, and an HTTPS application origin.
Reverse-proxy protocol headers are trusted only through the explicit
`TRUST_X_FORWARDED_PROTO` switch and only when the selected proxy overwrites or
removes incoming client values.

The repository contains provider-neutral example manifests only. Managed
databases, Redis, object storage, TLS, monitoring, and n8n remain external and
isolated. Provider, Saudi-region/data-residency, domains, billing, and named
operational owners require project-owner approval before any external resource
is created.

## Consequences

- The same immutable artifact can be promoted from staging to production.
- Static assets and localization catalogs are created during the build.
- Staging can be labeled and monitored correctly without weakening production.
- A platform-specific manifest may be added only after provider approval.
- The application image alone does not constitute a production deployment;
  backups, monitoring, TLS, SMTP, object storage, and operational ownership are
  still required.
