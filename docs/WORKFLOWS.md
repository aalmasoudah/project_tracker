# Workflows

## Account Lifecycle

1. An authorized administrator creates the account.
2. The administrator assigns one department and one approved predefined role.
3. The user signs in with a temporary hashed password and must replace it.
4. The user may change their password and persisted language preference.
5. Technical Admin may update non-security profile fields, reset a password,
   or deactivate/reactivate the account.
6. Deactivation revokes all sessions; reactivation requires a new login.
7. Lifecycle and role changes create append-only audit records.

Only a superuser may grant or revoke Technical Admin. Accounts are never
hard-deleted.

## Project and Course Lifecycle

Phase 3 project lifecycle:

1. Executive Manager or Project Manager creates a Draft project in an owning
   department with a required eligible manager.
2. The creator may assign an eligible supervisor and active department team
   members.
3. Executive Manager may manage any project. Project Manager may manage only
   a project for which they are the manager.
4. Draft may become Active or Cancelled; Active may become On Hold or
   Cancelled; On Hold may become Active or Cancelled; Cancelled may return to
   Draft.
5. Authorized actors archive instead of deleting. Archived projects are
   read-only until restored.
6. Project, status, team, archive, client, and category changes are audited.

Phase 4 course lifecycle:

1. Executive Manager or the owning Project Manager creates a Draft course
   inside a non-archived permitted project.
2. Draft may become Active or Cancelled; Active may become On Hold or
   Cancelled; On Hold may become Active or Cancelled; Cancelled may return to
   Draft.
3. A course may be Active only while its project is Active.
4. Authorized actors assign active external trainers and upload approved
   private files.
5. Course archive makes the course read-only and end-dates active trainer
   assignments. Restore does not reactivate prior assignments.
6. Course, trainer, assignment, file, status, archive, and restore actions are
   audited.

Project and course completion approval remain deferred to Phase 7.

## Task Lifecycle

Tasks may belong to projects or courses and may include subtasks, assignees,
dependencies, recurrence, comments, files, tags, status history, and approval.
Exact statuses, dependency rules, recurrence rules, and completion behavior
remain to be approved.

## Trainee Import

1. An authorized user uploads a CSV or Excel file.
2. The system validates format and content without committing data.
3. The user reviews a preview containing valid rows, warnings, duplicates,
   and errors.
4. The user confirms the import.
5. The system writes valid records in a transaction and records an audit
   entry.

Duplicate identity rules and partial-import behavior require approval.

## Trainer Attendance

1. An authorized user creates a scheduled session.
2. The system generates a random, expiring trainer link.
3. The external trainer opens the link and submits attendance.
4. The submission enters supervisor review.
5. The supervisor approves or rejects it.
6. Rejection requires a reason, reopens the same link, and assigns a new
   expiration.
7. Approved attendance is read-only through the trainer link.
8. An authorized internal correction requires a reason and audit entry and
   does not restart approval.

## Notifications

Business events create in-app notifications. Approved categories may also
send email through a background job. Jobs are idempotent and retry-safe.
Category rules, timing, recipients, and escalation require approval.

## Archive and Recovery

Authorized users archive important records. Restoration means restoring an
archived application record, not restoring a database backup. Database backup
restoration is handled through a documented operational procedure.

## Workflow Approval

Status: Account lifecycle, Phase 3 project lifecycle, and Phase 4 course
lifecycle are approved. Other phase-specific transitions and permissions
require later approval.
