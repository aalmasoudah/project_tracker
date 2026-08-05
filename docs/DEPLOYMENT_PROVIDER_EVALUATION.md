# Deployment Provider Evaluation

Date verified: 2026-08-05

Status: Technical recommendation complete; provider account and data-residency
approval remain external decisions.

## Recommendation

Use Google Cloud region `me-central2` (Dammam) for staging and production when
Saudi data residency is required or may become required. Use Render Frankfurt
only after the project owner explicitly confirms that application data may be
stored and processed outside Saudi Arabia.

The recommendation is intentionally conservative because this system can hold
university project, staff, trainee, attendance, approval, audit, and uploaded
file data. Choosing a non-Saudi region before policy review would create an
avoidable migration and compliance risk.

## Verified Service Fit

Google Cloud currently lists the following in Dammam:

- Cloud Run services for the Gunicorn web container.
- Cloud Run worker pools for continuous Celery worker and Beat containers.
- Cloud SQL for PostgreSQL.
- Memorystore for Redis.
- Cloud Storage in-region, with its XML API and HMAC authentication providing
  interoperability for S3-compatible libraries.
- Compute Engine as a fallback for the isolated n8n runtime.

The application mapping is:

| Application responsibility | Dammam service |
| --- | --- |
| Immutable image registry | Artifact Registry |
| Django/Gunicorn web | Cloud Run service |
| Celery task execution | Cloud Run worker pool, one or more instances |
| Celery Beat | Separate Cloud Run worker pool, exactly one instance |
| PostgreSQL | Private Cloud SQL for PostgreSQL |
| Redis broker | Private Memorystore for Redis |
| Private uploads | Regional Cloud Storage bucket through XML/S3 API |
| Secrets | Secret Manager with service-specific IAM |
| Migrations | One-off Cloud Run job using the promoted image |
| Logs/metrics/uptime | Cloud Logging and Cloud Monitoring |
| n8n | Separate secured service or Compute Engine deployment and database |

The existing Phase 18 image supports these roles without modification. Only
the worker receives `GROQ_API_KEY`; web, Beat, migration, and n8n services do
not receive it.

## Render Alternative

Render is simpler to operate and directly supports Docker web services,
continuous Celery background workers, managed PostgreSQL, and Redis-compatible
Key Value. Its currently documented regions are Oregon, Ohio, Virginia,
Frankfurt, and Singapore. It has no Saudi region, so it is not the default for
this project.

If non-Saudi hosting is approved, use Frankfurt and keep staging and production
in separate protected environments. Private S3-compatible storage and SMTP
would still require separate providers.

## Known Dammam Considerations

- Cloud Run's direct domain-mapping feature is not listed for Dammam. Staging
  can use the generated `run.app` HTTPS domain; production should use an
  external HTTPS load balancer and managed certificate for a custom domain.
- Worker pools run continuously and therefore have continuous compute cost.
- A private VPC path is required between Cloud Run, Cloud SQL, and Memorystore.
- The Cloud Storage XML/S3 path must pass upload, authorized download, filename,
  size, and private-access tests with the exact Django storage configuration.
- SMTP is not selected. The provider must support authenticated TLS on port 587,
  approved sender-domain authentication, and the organization's data policy.
- n8n must remain isolated from the application database, Redis, S3 credentials,
  and Groq key. It receives only its own PostgreSQL/Telegram credentials and the
  narrow HMAC secrets already defined by Phases 16 and 17.

## Inputs Required Before Provisioning

1. Written confirmation whether Saudi data residency is mandatory.
2. A Google Cloud organization/project with billing enabled and an approved
   account owner, or explicit approval to use Render Frankfurt instead.
3. An authenticated SMTP provider/account and approved staging sender address.
4. Named release, security, backup, and support owners.

A custom domain is not required for the first Dammam staging deployment because
the generated Cloud Run HTTPS origin can be used. No external resource should
be created until the account owner and budget are confirmed.

## Current Official Sources

- Google Cloud locations: <https://cloud.google.com/about/locations>
- Cloud Run locations: <https://cloud.google.com/run/docs/locations>
- Cloud Run worker pools: <https://cloud.google.com/run/docs/deploy-worker-pools>
- Cloud SQL PostgreSQL regions:
  <https://cloud.google.com/sql/docs/postgres/region-availability-overview>
- Memorystore pricing/regions:
  <https://cloud.google.com/memorystore/docs/redis/pricing>
- Cloud Storage S3 interoperability:
  <https://cloud.google.com/storage/docs/interoperability>
- Render regions: <https://render.com/docs/regions>
- Render service types: <https://render.com/docs/service-types>
