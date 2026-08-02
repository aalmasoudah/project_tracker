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

Project and course completion use the Phase 7 approval workflow below.

## Task Lifecycle

Phase 5 task lifecycle:

1. Executive Manager or the owning Project Manager creates a To Do task under
   exactly one non-archived project or course.
2. A task has one or more eligible assignees, exactly one active primary
   owner, and up to three acyclic same-owner hierarchy levels.
3. To Do may become In Progress or Cancelled; In Progress may become Blocked,
   Completed, or Cancelled; Blocked may become In Progress or Cancelled;
   Completed may return to In Progress; Cancelled may return to To Do.
4. Blocked requires a reason. An assignee may update only status, actual
   hours, and blocking reason.
5. Authorized collaborators add immutable comments and approved private
   files. Managers select and administer bilingual tags.
6. Archive makes a task read-only, end-dates active assignments and tag links,
   and requires subtasks to be archived first. Restore recreates the latest
   still-eligible assignment set without rewriting history.
7. Task, assignment, status, comment, file, tag, archive, and restore actions
   create append-only task-scope audit events.

Dependencies, recurrence, task approvals, watchers, and notifications remain
deferred.

## Progress Calculation

Phase 6 progress is calculated on demand through one service:

1. Completed leaf tasks are 100 percent; other countable leaf statuses are
   0 percent.
2. Cancelled/archived task branches are excluded.
3. Parent tasks average direct countable children recursively.
4. Courses average top-level course tasks.
5. Projects equally average available direct-task and course categories.
6. Empty and excluded states are explicit; public values are Decimal-safe,
   bounded, and rounded half-up to two decimal places.

Milestones, approvals, attendance components, dashboards, and reports extend
the same service only in their approved later phases.

## Milestone and Completion Approval

1. Executive Manager or the owning Project Manager maintains milestones.
2. An eligible task, course, milestone, or project completion is submitted.
3. The project Supervisor decides first.
4. Approval advances the request to the Project Manager; rejection requires a
   reason and returns the target to active work.
5. Project Manager approval completes the request and its target.
6. A rejected target may be resubmitted as a new attempt; prior attempts and
   decisions remain immutable.
7. Pending targets cannot be normally edited or archived. Phase 7 has no
   override.

## Trainee Import

1. An authorized user uploads a CSV or Excel file.
2. The system validates format and content without committing data.
3. The user reviews a preview containing valid rows, warnings, duplicates,
   and errors.
4. Existing-course duplicates are explicitly skipped or updated. A duplicate
   repeated inside the same file can only be skipped.
5. Errors block confirmation. The system locks the course, rechecks duplicate
   and capacity state, and writes every valid resolution atomically.
6. The system allocates new course-specific trainee numbers in original file
   order and records an audit entry.
7. Cancellation retains protected preview evidence but writes no trainees.

## Trainer Attendance

1. An authorized user creates a scheduled session.
2. The system generates a random, expiring trainer link.
3. The external trainer opens the link and submits attendance.
   The link is token-bound to one session, expiry is rechecked on submit, and
   every locked trainee requires Present, Absent, Late, or Excused.
4. The submission enters supervisor review.
5. The supervisor approves or rejects it.
6. Rejection requires a reason, reopens the same link, and assigns a new
   expiration.
7. Approved attendance is read-only through the trainer link.
8. An authorized internal correction requires a reason and audit entry and
   does not restart approval.

## Notifications

Task assignment, approval, deadline/overdue, and mention events create
permission-safe in-app notifications. Approval alerts are mandatory in-app;
users configure the other in-app channels and all email channels. Email is
queued after the domain transaction commits.

At 08:00 Asia/Riyadh, scheduled work creates one active-assignee reminder for
tasks due tomorrow and one reminder for each overdue day. Completed,
cancelled, archived, and cancelled-owner-context tasks are excluded. Stable
recipient/event keys deduplicate notification creation, and bounded Celery
jobs record retry-safe delivery state. Phase 11 has no escalation chain.

## Archive and Recovery

Authorized users archive important records. Restoration means restoring an
archived application record, not restoring a database backup. Database backup
restoration is handled through a documented operational procedure.

## Workflow Approval

Status: Account lifecycle and Phase 3 through Phase 10 domain lifecycles are
approved. Other phase-specific transitions and permissions require later
approval.
