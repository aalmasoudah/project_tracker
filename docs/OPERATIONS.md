# Operations Plan

## Status and Purpose

Status: Phase 14 application and recovery policy approved. Provider details,
named contacts, and production routing remain production-readiness inputs.

This plan defines the operational capabilities required before company data is
placed in production. Named owners, escalation contacts, retention periods,
provider plans, and recovery objectives still require approval.

## Operational Responsibilities

Before staging, assign owners for:

- Application releases and rollback.
- Database and object-storage administration.
- Security incident response.
- User access and periodic permission review.
- Backup verification and restoration tests.
- Monitoring and alert response.
- Email delivery and domain authentication.
- Data retention, privacy requests, and audit access.
- User support and escalation.
- Arabic terminology/translation review and localization release quality.

Production credentials must be role-limited and unavailable to ordinary
application users.

Approved responsibility separation:

- The project owner owns business-data, privacy, retention, and audit policy.
- Technical Admin owns application access administration and safe in-app
  health/backup-status review.
- A separately authorized infrastructure operator owns releases, database and
  storage access, backup execution, and isolated restoration. Application
  roles do not grant shell or provider access.

## Monitoring

Monitor at minimum:

| Area | Signals |
| --- | --- |
| Availability | Health endpoint, external uptime, failed releases |
| Application | Error rate, response latency, slow requests |
| Security | Abnormal authentication/token failures, denied sensitive actions |
| Database | Capacity, connections, locks, slow queries, backup status |
| Storage | Capacity, authorization failures, lifecycle failures |
| Workers | Queue depth, worker availability, retry/failure rate |
| Email | Bounce/failure rate and provider health |
| Business workflows | Stuck approval/import/attendance states where measurable |

Alert thresholds, on-call routes, and escalation timing require operational
approval and measured baselines.

## Health Endpoint

`/health/` reports application and database availability using a stable,
machine-readable response. It must:

- Avoid secrets, configuration values, stack traces, record counts, and
  internal topology.
- Use an appropriate failure status when the database is unavailable.
- Remain inexpensive and safe for frequent platform probes.
- Expand to worker/storage dependencies only when doing so improves actionable
  monitoring without making the web service appear unhealthy for a separate
  degraded dependency.

## Backup and Recovery

- Use managed PostgreSQL recovery capabilities appropriate to the production
  plan.
- Create encrypted logical backups stored separately from the primary service
  where approved.
- Back up object metadata and ensure object-storage durability/versioning
  aligns with policy.
- Verify backup jobs and alert on failure.
- Restore into an isolated temporary environment, apply checks, and validate
  important record counts/workflows.
- Record restoration evidence, elapsed time, owner, and outcome.
- Securely remove temporary restoration resources.

The approved initial targets are:

- Recovery point objective: 24 hours.
- Recovery time objective: 8 hours.
- Encrypted backup retention: 35 days.
- Isolated restoration test: quarterly.
- Application records/files/audit/archive retention: indefinite for the
  initial release, with no automated purge.

The application must not expose an unrestricted database-restore web page.

## Incident Response

1. Detect and classify the incident.
2. Assign an incident lead and establish a timestamped record.
3. Contain access or pause affected workflows without destroying evidence.
4. Preserve relevant logs, release identifiers, and database/storage state.
5. Recover using an approved runbook and verified source.
6. Validate authorization, integrity, and critical workflows.
7. Communicate through approved contacts.
8. Complete a post-incident review and track corrective actions.

Security incidents must include credential/token revocation and access review
where applicable. Direct production data edits require an approved,
auditable procedure.

## Routine Maintenance

- Review dependency and security updates regularly in staging first.
- Review errors, failed jobs, storage/database capacity, and email failures.
- Verify backup completion and perform approved restoration exercises.
- Review inactive accounts, privileged groups, and service credentials.
- Rotate secrets according to approved policy and after suspected exposure.
- Review slow queries and indexes using realistic synthetic data.
- Maintain change log, decision records, runbooks, and release history.
- Review translation completeness and Arabic rendering whenever user-visible
  text, emails, imports, or reports change.

## Protected Operational Commands

Management commands that export data, apply retention, repair state, or create
privileged users must:

- Require an explicit environment and confirmation mechanism appropriate to
  impact.
- Validate authorization through operational access controls.
- Be idempotent or safely resumable where practical.
- Support dry-run for destructive or broad changes.
- Log safe summaries without secrets or personal payloads.
- Refuse ambiguous targets.

These commands are added only in the phase that owns their behavior.

## Notification Worker Runbook

- Run one or more Celery workers with `celery -A config worker`; Windows local
  development uses `--pool=solo`.
- Run exactly one Celery Beat scheduler with `celery -A config beat`.
- Monitor pending/retry/failed delivery records and Redis queue depth. Only
  Technical Admin has application access to delivery status.
- A dispatcher retries due pending records every minute and recovers
  processing records left stale for 15 minutes.
- Delivery is attempted at most four times with bounded backoff. Stored errors
  contain only an exception class, never provider responses, addresses, or
  message content.
- After an outage, restore Redis/worker availability and let the dispatcher
  resume due records. Do not reset sent records or manually replay business
  events.
- Development uses console email and tests use in-memory email. Production
  requires the HTTPS application origin, Redis URL, authenticated SMTP
  credentials, and an approved sender address.

## Required Runbooks Before Launch

The Phase 14 application command, retention, audit-export, archive, backup
verification, and isolated restoration procedure is documented in
`docs/RUNBOOKS/PHASE_14_OPERATIONS.md`.

- Deploy and rollback.
- Create/revoke privileged access.
- Database backup verification and isolated restoration test.
- Object-storage access failure.
- Suspected credential or token exposure.
- High error rate or unavailable service.
- Failed migration.
- Worker backlog/failure after Phase 11.
- Email delivery failure after Phase 11.
- Privacy, retention, and authorized data export.

## Open Operational Decisions

- Named owners, support contact, and escalation path.
- Production region, provider plans, and contractual requirements.
- Provider implementation of the approved RPO, RTO, backup retention, and
  quarterly restoration cadence.
- Any future change from indefinite application-data retention or any
  hard-delete exception.
- Monitoring thresholds and notification routes.
- Maintenance windows and release approval authority.
- Staging and production domain names.
- Default language, approved Arabic terminology owner, calendar/digit policy,
  and Arabic support contact.
