# Phase 14 Operations and Recovery Runbook

Status: Application procedure verified; provider-specific steps and named
contacts must be completed before production.

## Authority and Safety Boundary

- The project owner approves business-data, privacy, retention, audit, and
  export policy.
- Technical Admin manages application access and reviews the safe in-app
  operations page.
- Only a separately authorized infrastructure operator may access hosting,
  database, storage, backup, release, or shell controls.
- Application roles never grant provider or shell access.
- Database restoration is never initiated from the application. Do not add a
  restore URL, button, arbitrary SQL console, file browser, credential view,
  or backup-content view.

Before staging, replace these controlled placeholders in the private operator
handbook (not this repository): named project owner, infrastructure operator,
security incident lead, support contact, escalation channel, provider/region,
database plan, object-storage plan, monitoring route, and maintenance window.

## Approved Targets

- RPO: 24 hours.
- RTO: 8 hours.
- Encrypted backup retention: 35 days.
- Isolated restoration exercise: at least quarterly.
- Application records/files/audit/archive retention: indefinite; no purge.

## Backup Verification

1. Confirm the provider backup job completed for the intended environment.
2. Confirm encryption, separate storage/recovery capability, and the recovery
   point timestamp through provider controls. Do not copy credentials or
   backup identifiers into application logs.
3. Run a dry-run from an authorized release shell whose
   `DEPLOYMENT_ENVIRONMENT` exactly matches the target:

   ```text
   python manage.py record_backup_status --environment staging --kind backup --status succeeded --completed-at 2026-08-02T00:00:00Z
   ```

4. Review the exact dry-run summary. To record the safe status, repeat with:

   ```text
   --apply --confirm RECORD-BACKUP-STATUS:staging
   ```

5. Verify the Technical Admin operations page shows the expected freshness.
   A failed or stale status requires escalation; never falsely record success.

The command stores only environment, kind, result, completion time, and an
idempotency key. It never reads backup contents or performs a restoration.

## Quarterly Isolated Restoration Exercise

1. Open an approved change/incident record and identify the authorized source
   recovery point. Confirm the temporary environment contains no production
   integrations, outbound email, public links, or shared credentials.
2. Create an isolated temporary database and private storage location using
   provider controls. Restrict access to the restoration team.
3. Restore through provider/database tooling outside the application. Preserve
   provider evidence and elapsed time in the private operator record.
4. Deploy the matching application version, apply only reviewed forward
   migrations if required, and run Django checks.
5. Validate fictionalized or approved integrity totals for critical domains:
   accounts/departments, projects/courses/tasks, approvals, trainees,
   attendance, notifications, and audit history. Do not place raw personal
   values in tickets or logs.
6. Execute permission-safe Arabic/English smoke workflows and confirm private
   files remain access-controlled.
7. Compare the observed recovery point/time with the 24-hour RPO and 8-hour
   RTO. Escalate any miss before production approval.
8. Record the safe restoration-test result using `--kind restore_test`, first
   dry-run and then the exact environment confirmation from the backup command.
9. Securely remove the isolated resources through provider controls after the
   evidence is approved. Never delete application audit evidence.

## Retention Inventory

Run the non-destructive inventory from an authorized shell:

```text
python manage.py retention_inventory --environment staging
```

It reports protected model counts, policy `indefinite`, and exactly zero
deletion candidates. It has no delete mode. To retain an idempotent safe
summary after review, repeat with:

```text
--record --confirm RECORD-RETENTION-INVENTORY:staging
```

Any request to purge, hard-delete, shorten retention, add legal-hold
exceptions, or export personal data must stop and obtain a new owner decision,
privacy/security review, verified backup, dry-run evidence, and rollback
analysis.

## Authorized Audit Export

- Technical Admin exports only security/operations audit.
- CEO and Executive Manager export only business audit.
- Use a range of 366 days or fewer and no more than 5,000 rows.
- The CSV contains safe columns only and is never retained by the application.
- Store any downloaded file only in an approved private location and dispose
  of it under the applicable business process.
- Audit export itself creates a safe operations event.

## Archive and Restore of Application Records

Use the archive center only to locate records. Every restore link opens the
existing domain confirmation workflow, which rechecks current permission,
object scope, parent state, dependencies, and constraints. A failed restore
must be corrected through normal domain workflows; do not bypass the service
with SQL. Session restoration and database restoration are not approved.

## Failure and Escalation

- Backup failed/stale: notify the infrastructure operator and project owner,
  preserve evidence, pause risky releases, and restore backup coverage.
- Operations page unavailable: check the public minimal health endpoint and
  platform/database state without exposing internal diagnostics to users.
- Suspected credential/token exposure: revoke/rotate affected credentials,
  contain integrations, preserve logs/audit evidence, and follow incident
  response in `docs/OPERATIONS.md`.
- Data-integrity concern: stop writes/releases where practical, preserve the
  current state, and use the isolated recovery procedure. Never “repair” with
  unreviewed production SQL.

## Required Exercise Record

Keep the following in the approved private operations system: change/incident
reference, environment, authorized owner/operator, source recovery point,
start/end times, observed RPO/RTO, application version, migration state,
checks performed, outcome, follow-up actions, evidence location, and approval.
Do not commit credentials, backup identifiers, real personal data, or backup
files to this repository.
