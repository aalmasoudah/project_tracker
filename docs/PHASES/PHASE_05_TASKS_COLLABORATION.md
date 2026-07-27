# Phase 5: Tasks and Collaboration

Status: Completed and verified on 2026-07-27.

## 1. Goal

Implement approved project/course tasks, bounded subtasks, assignments,
comments, tags, files, and complete history without dependencies, recurrence,
approvals, or progress formulas.

## 2. Included Features

- Task create, list/filter, detail, edit, archive/restore.
- Exactly one approved owner context: project or course.
- Subtasks up to the approved maximum depth.
- Assignees, one primary owner, dates, status, priority, hours, and blocking
  reasons.
- Immutable comments, bilingual tags, private files, and audit history.
- Arabic/English content and complete RTL/LTR task workflows.

## 3. Excluded Features

- Task/course/project progress calculation.
- Milestone or project-completion approval workflows.
- Notification delivery, dashboards, Kanban, calendar, Gantt, and reports.
- Any status, recurrence, dependency, or approval behavior not approved.
- Dependencies, recurrence, task approvals, and watchers.

## 4. User Stories

- As an authorized manager, I can create and organize tasks in a permitted
  project/course.
- As an approved assignee, I can view/update the allowed task fields.
- As a collaborator, I can comment, tag, and attach approved files.
- As an Arabic-speaking user, I can complete the full workflow in RTL without
  loss of Arabic task/comment text.

## 5. Models Involved

- `tasks.Task`, `TaskAssignment`.
- `TaskComment`, `Tag`, task-tag relationship, task file relationship.
- Append-only task-scope `audit.AuditEvent` records.

## 6. Pages Involved

- Task list/filter, create, detail, edit, archive/restore.
- Subtask, assignment, comments, tags, files, and history sections.

## 7. Permission Requirements

The action matrix must distinguish task create/view/update/archive,
assignment, comments, files, and history for project/course contexts.
Querysets inherit approved owner access and prevent cross-project/course
object references.

## 8. Validation Rules

- A task has exactly one supported owner and an accessible parent context.
- Parent chains are acyclic and within approved depth.
- Status transitions, dates, assignments, and archive behavior follow
  decision 0010.
- Arabic text is preserved; search normalization never replaces source text.
- Comments/tags/files enforce size, content, and authorization limits.

## 9. Business Rules

- Phase 5 rules and permissions are recorded in decision 0010.
- Progress and cancelled-denominator behavior remain deferred to Phase 6.
- Important tasks/comments/history use approved archive/delete behavior.

## 10. Expected Migrations

- Initial task, assignment, comment, tag, task-tag, and file models.
- Check/unique constraints and indexes for owner, parent, assignee, status,
  priority, dates, and archive reads.

## 11. Unit Tests

- Task forms and owner/parent validation.
- Nesting-depth and cycle detection.
- Hierarchy, transition, assignment, hours, blocking, and archive policy.
- Comment/tag/file validation and localized labels/errors.

## 12. Integration Tests

- Authorized task lifecycle in projects and courses.
- Cross-context/object denial and form tampering.
- Transactions for assignment, tag, archive, and multi-record changes.
- History completeness, constraints, and list/detail query counts.
- Arabic content/filter round-trip.

## 13. Browser Tests

- Create, assign, update, comment on, and archive a task.
- Build subtasks up to approved boundaries and see useful errors.
- Run the primary workflow in Arabic RTL and representative English LTR.

## 14. Security Tests

- Unauthorized assignment and status changes.
- Cross-project/course IDs, direct URLs, restricted comments/history/files.
- CSRF/method safety, upload validation, and stored content escaping/
  bidirectional isolation.

## 15. Manual Verification

- Exercise task lifecycle for each relevant role.
- Verify depth, assignments, status, history, files, and archive.
- Review Arabic terminology, long titles/comments, mixed identifiers, RTL
  tables/forms, and localized validation.

## 16. Acceptance Criteria

- Approved task/subtask/assignment behavior is enforced.
- Task lifecycle and history are transactional, authorized, and auditable.
- Project/course object access is preserved for every related record.
- Arabic/English task workflows and data pass localization verification.
- No progress, milestone approvals, notifications, or operational views are
  implemented.

## 17. Dependencies

- Completed Phases 3 and 4.
- Approved Phase 5 decision 0010.
- Approved Arabic terminology and normalization policy.
- Task approvals are deferred to Phase 7.

## 18. Rollback Considerations

- Preserve task history/comments/files and task-scope audit evidence.
- Hierarchy constraint changes require preflight validation and a staged
  migration.
