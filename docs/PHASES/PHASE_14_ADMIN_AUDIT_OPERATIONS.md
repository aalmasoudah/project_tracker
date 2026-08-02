# Phase 14: Administration, Audit, and Operational Safety

Status: Approved under decision 0019; implemented and verified on 2026-08-02.

## 1. Goal

Provide authorized audit viewing, archive management, approved data export,
safe health/backup-status visibility, protected management commands,
retention behavior, and launch-ready operations documentation without a web
database-restore feature.

## 2. Included Features

- Permission-scoped audit viewer and filters.
- Approved cross-domain archive/restore management.
- Approved administrative data exports.
- Safe operational health and backup-status visibility.
- Protected, dry-run-capable management commands.
- Approved retention enforcement and operations/recovery runbooks.
- Arabic/English administrative presentation and complete RTL/LTR workflows.

The approved retention behavior is non-destructive: protected application
data is retained indefinitely and the retention command reports inventory
with zero deletion candidates.

## 3. Excluded Features

- Unrestricted database restore in the web UI.
- Direct arbitrary SQL/file-browser/secret display.
- Retention, deletion, override, or export behavior without approval.
- Production infrastructure creation not authorized by the owner.

## 4. User Stories

- As an authorized auditor, I can find relevant safe audit events.
- As an authorized archivist, I can restore approved application records.
- As an operator, I can inspect safe health/backup status and run protected
  commands with clear scope/dry-run behavior.
- As an Arabic-speaking authorized administrator, I can use all approved
  interfaces in RTL while stable machine codes remain unambiguous.

## 5. Models Involved

- Existing `audit.AuditEvent` and domain archive fields.
- Optional protected export/operation/retention-run metadata.
- No model containing secrets or raw database backup contents.

## 6. Pages Involved

- Audit list/detail/filter.
- Archive list/detail/restore confirmation.
- Approved data export form/status.
- Safe health/backup-status page for approved roles.
- Operations documentation links; no restore action.

## 7. Permission Requirements

Decision 0019 resolves `RBAC-08`, `RBAC-09`, export rights, personal-data
access, and operational role separation. View, export, archive, restore,
retention, and shell command execution remain distinct permissions.

## 8. Validation Rules

- Filters/date ranges/export sizes and target record types are allowlisted.
- Restore revalidates current constraints and permissions.
- Protected commands require explicit environment/target, safe confirmation,
  and dry-run for broad/destructive work.
- Retention uses approved policy, preserves required holds/audit, and reports
  exact scope before action.
- Audit/action codes remain stable; Arabic/English labels are presentation.

## 9. Business Rules

- Important records are archived rather than normally deleted.
- Database restoration is an infrastructure operation, not a general web
  action.
- Decision 0019 resolves `BR-16`, `BR-18`, `RBAC-07` through `RBAC-09`,
  retention/legal-hold behavior, backup/RPO/RTO, operation ownership, and
  localization policy.

## 10. Expected Migrations

- Only approved operation/export/retention metadata or missing audit indexes/
  constraints.
- Domain archive changes require separate reviewed migrations and backfills.

## 11. Unit Tests

- Audit redaction/presentation and localized action labels.
- Archive/restore eligibility.
- Export scope/format safety.
- Retention selection and protected command confirmation/dry-run.
- Safe health/backup status shaping.

## 12. Integration Tests

- Audit access/filtering and cross-object denial.
- Archive/restore across approved record types with constraints/history.
- Export authorization and personal-data scope.
- Management command protections/idempotency and retention logic.
- Health/backup visibility without secrets.

## 13. Browser Tests

- Authorized/unauthorized audit, archive/restore, export, and health access.
- Primary administrative workflow in Arabic RTL and English LTR.
- Verify destructive confirmations, long audit data, pagination, and keyboard
  access.

## 14. Security Tests

- Secret/token/personal payload redaction.
- Direct audit/export/archive/health URLs and forged targets.
- Spreadsheet/file injection, excessive exports, command environment mistakes,
  retention overreach, CSRF/method safety, and audit tampering attempts.

## 15. Manual Verification

- Inspect audit history for every critical workflow.
- Archive/restore each approved record type using fictional data.
- Run protected commands in staging dry-run and approved execution modes.
- Verify backup status and follow an isolated restoration runbook outside the
  web UI.
- Review Arabic terminology, mixed structured data, RTL tables, exports, and
  operational documentation.

## 16. Acceptance Criteria

- Only approved roles access audit, archive, export, health, and operations.
- Audit data is complete, safe, and normally immutable.
- Archive/restore and retention match approved policy.
- Commands are protected, scoped, auditable, and dry-run-capable where needed.
- Health/backup views leak no secrets.
- Arabic/English administrative workflows pass localization verification.
- No unrestricted web database restoration exists.

## 17. Dependencies

- Completed prior phases and consistent audit/archive behavior.
- Decision 0019 and completed prior phases define audit/health/export/restore
  permissions, retention/hard-delete/legal-hold behavior, operational
  ownership, backup/RPO/RTO, and protected command policy.
- Approved Arabic operational terminology and date/digit policy.

## 18. Rollback Considerations

- Never roll back by deleting audit/operation evidence.
- Retention actions are inherently destructive and require verified backups,
  dry-run evidence, exact targets, and phase-specific rollback limitations.
- Archive schema changes require compatibility across mixed application
  versions.
