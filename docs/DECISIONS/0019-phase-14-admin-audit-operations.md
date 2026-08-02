# Decision 0019: Phase 14 Administration, Audit, and Operational Safety

Status: Approved on 2026-07-30.

- Technical Admin may view and export sanitized security and operations audit
  events. CEO and Executive Manager may view and export sanitized business
  audit events. Technical Admin receives no business-domain audit visibility.
  Audit metadata is hidden unless its key is explicitly allowlisted.
- The archive center reuses existing domain permissions and object scopes.
  Technical Admin manages archived departments, Executive Manager manages all
  supported business archives, and Project Manager manages only already
  approved managed-project records plus globally managed task tags. It creates
  no archive override and does not add session or database restore.
- Phase 14 administrative export is limited to a bounded, filtered, sanitized
  audit CSV. Trainee contacts, individual attendance, uploaded files, raw
  metadata, and other personal-data exports remain excluded.
- Application business records, uploaded files, notifications, delivery
  evidence, audit records, and archived data are retained indefinitely for the
  initial release. Phase 14 contains no automated purge or hard-delete path.
  A retention inventory may report exact protected scope but has zero deletion
  candidates.
- Technical Admin may view a safe operations page containing application,
  database, retention, recovery-target, and recorded backup-verification
  status. It exposes no credentials, topology, backup contents, record counts,
  or restoration action.
- Database backup and restoration remain infrastructure operations performed
  by an authorized shell operator. Protected commands require an exact
  configured environment, are dry-run by default where they write state, use
  explicit confirmation for recording, and create idempotent safe audit
  summaries without secrets or personal payloads.
- The initial recovery targets are an RPO of 24 hours and an RTO of 8 hours.
  Encrypted backups are retained for 35 days, and an isolated restoration test
  is required quarterly. Provider configuration and named contacts remain
  production-readiness inputs rather than application defaults.
- Phase 14 supports Arabic and English in RTL/LTR. Administrative dates use
  Asia/Riyadh time and display Gregorian plus Umm al-Qura Hijri values using
  Western digits.
- Approved Arabic terminology includes Audit log `سجل التدقيق`, Archive
  management `إدارة الأرشيف`, Operations `العمليات`, System health
  `سلامة النظام`, Backup status `حالة النسخ الاحتياطي`, Retention policy
  `سياسة الاحتفاظ`, and Restore `استعادة`.
