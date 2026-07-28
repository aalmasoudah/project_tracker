# Data Model Plan

## Status and Purpose

Status: Planning baseline. Model names and relationships are architectural
guidance, not approval of unresolved business behavior.

The database is PostgreSQL in every environment. The model is divided by
business domain so that permissions, transactions, migrations, and ownership
remain understandable as the system grows.

## Modeling Principles

- Create the custom user model before the first application migration.
- Use stable primary keys and explicit foreign-key deletion behavior.
- Archive important business records instead of deleting them normally.
- Add database constraints for invariants that must never be violated.
- Put multi-record writes in transactional services.
- Keep calculated progress out of stored fields unless an approved,
  invalidation-safe design requires caching.
- Store file metadata in PostgreSQL and production file bytes in private
  S3-compatible storage.
- Add indexes for foreign keys, archive flags, status/date filters, approval
  queues, token lookups, and other measured query paths.
- Do not add generic polymorphic models when explicit domain relationships are
  clearer.
- Use PostgreSQL UTF-8 encoding and preserve Arabic text exactly as entered;
  search/duplicate normalization must not overwrite source text.

## Domain Ownership

| Domain app | Planned responsibility | Earliest phase |
| --- | --- | --- |
| `accounts` | Custom user identity and account lifecycle | 1 |
| `organizations` | Departments and organization membership | 2 |
| `projects` | Projects, clients, categories, teams, and project files | 3 |
| `courses` | Courses, trainers, schedules, capacity, and course files | 4 |
| `tasks` | Project/course tasks, bounded hierarchy, assignments, comments, files, and tags | 5 |
| `progress` | Calculation-only task/course/project progress services and authorized selectors | 6 |
| `approvals` | Milestones and completion/task approval state/history | 7 |
| `trainees` | Trainees and transactional import batches | 8 |
| `attendance` | Sessions, secure trainer links, submissions, review, and corrections | 9 |
| `notifications` | In-app notifications, preferences, and delivery records | 11 |
| `reports` | Report orchestration; no duplicate source-of-truth records | 13 |
| `files` | Shared upload metadata and validated storage access | First phase that needs uploads |
| `audit` | Append-only security and business audit events | First audited workflow |

Apps are introduced only when their approved phase requires them. This table
does not authorize creating empty placeholder apps in Phase 1.

## Planned Entity Groups

### Identity and Organization

- `accounts.User`: a custom Django user created in Phase 1. It begins with only
  the fields required for authentication compatibility. Business profile,
  department, and lifecycle behavior belong to Phase 2.
- An approved persisted language preference belongs to Phase 2; Phase 1 uses
  session/cookie/request localization without adding profile behavior.
- `organizations.Department`: organization unit; exact required fields and
  visibility rules require Phase 2 approval.
- Django `Group` and `Permission`: initial internal role mechanism.
- External trainers are not assumed to be users.

Open gate: the permission matrix and object-level access questions in
`USER_ROLES.md` must be approved before Phase 2.

### Projects and Courses

- `projects.Project`, `Client`, `Category`, and `ProjectMembership` are
  candidates for Phase 3.
- `courses.Course`, `Trainer`, and schedule/capacity records are candidates
  for Phase 4.
- Files and custom fields should use explicit ownership and validation rather
  than unbounded key-value storage unless the phase specification approves a
  constrained design.

Open gate: project/course statuses, transitions, archive rules, budget
visibility, currency, rounding, and object-level access are unresolved.

### Tasks and Progress

- `tasks.Task` references exactly one project or course through explicit
  nullable relationships and a database constraint.
- A self-referential parent relationship models an approved acyclic maximum
  of three levels within one owner context.
- `TaskAssignment`, `TaskComment`, `Tag`, `TaskTag`, and `TaskFile` preserve
  collaboration and lifecycle history. Task events use append-only
  task-scoped audit records.
- Progress is calculated by one approved service shared by dashboards and
  reports.

Open gate: progress formulas, cancelled denominator behavior, dependencies,
recurrence, and task approvals remain unresolved/deferred.

### Milestones and Approvals

- `approvals.Milestone` belongs to a project.
- Approval requests, steps, decisions, and history should be explicit records
  rather than a collection of loosely related flags.
- Approval transitions use locked rows and atomic transactions.

Open gate: approval steps, order, authorized actors, rejection/reopen rules,
and their effects on project completion are unresolved.

### Trainees and Imports

- `trainees.Trainee` holds the approved trainee identity fields.
- `ImportBatch` and `ImportRow` retain preview status, validation outcomes,
  and confirmation/audit metadata without committing unapproved rows.
- Import confirmation writes valid records atomically according to the
  approved partial-import rule.

Open gate: duplicate identity, allowed file columns, partial-import behavior,
and personal-data visibility are unresolved.

### Sessions and Attendance

- `attendance.Session` represents a scheduled course occurrence.
- `TrainerLink` stores a hash of a random token, expiry, state, and lifecycle
  metadata. Raw tokens are not stored where hash verification is practical.
- Attendance submissions, line items, reviews, rejection reasons, and
  correction history are explicit records.
- Approved attendance becomes read-only through the external link.

Confirmed lifecycle: submission requires supervisor approval; rejection
requires a reason and reopens the same link with a new expiration; authorized
correction requires a reason and audit entry without reapproval.

Open gate: attendance values, expiry-during-entry behavior, session time
semantics, and actor permissions are unresolved.

### Notifications, Reports, Files, and Audit

- Notifications record recipient, approved category, read state, source
  reference, and deduplication identity.
- Delivery attempts are separate from the in-app notification so retries do
  not duplicate business events.
- Reports query domain selectors and centralized progress services; report
  output is not a second source of truth.
- File records track ownership, storage key, original name, size, declared
  content type, detected content type, and security-relevant lifecycle data.
- Audit events are append-only and capture actor, action, target, timestamp,
  request correlation data, and a safe structured change summary.

Open gate: notification preferences, retention periods, report authorization,
and hard-deletion exceptions are unresolved.

## Relationship Outline

```text
User --< Department membership / Groups
Project --< ProjectMembership >-- User
Project --< Course --< Session --< AttendanceSubmission
Project or Course --< Task --< TaskAssignment >-- User
Task --< Task (approved bounded nesting)
Project --< Milestone --< ApprovalRequest --< ApprovalDecision
Course --< Trainee enrollment >-- Trainee
Session --< TrainerLink
ImportBatch --< ImportRow --> Trainee
Domain records --< FileRecord
Domain events --< Notification / AuditEvent
```

This is a planning outline. Exact cardinality, optionality, and field
requirements are finalized only in an approved phase.

## Migration Strategy

1. Phase 1 creates the custom user model and its initial migration before any
   other application model depends on it.
2. Each later phase owns migrations for only its approved models and
   constraints.
3. Schema and data migrations are separated when doing so makes rollback and
   review safer.
4. Potentially blocking constraint additions use a staged backfill and
   validation plan.
5. Deployed migrations are immutable unless explicit authorization says
   otherwise.
6. Every phase runs `makemigrations --check` and reviews generated SQL or
   operations in proportion to migration risk.

## Data Decisions Still Required

The remaining open questions in `BUSINESS_RULES.md` and `USER_ROLES.md` still
gate their listed later phases. Approved decisions 0007 through 0010 govern
the implemented account, project, course, and task models.
