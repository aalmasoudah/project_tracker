# Workflows

## Account Lifecycle

1. An authorized administrator creates the account.
2. The administrator assigns department and predefined groups.
3. The user signs in with a hashed password.
4. Authorized staff may deactivate or reactivate the account.
5. Lifecycle and role changes create audit records.

Detailed authorization remains to be approved before Phase 2.

## Project and Course Lifecycle

Projects contain teams and may contain courses, tasks, milestones, files, and
approval history. Exact statuses, transitions, required fields, and approval
steps remain to be approved.

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

Status: High-level workflows only. Phase-specific transitions and permissions
must be approved before implementation.
