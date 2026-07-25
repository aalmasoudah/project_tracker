# Phase 5: Tasks and Collaboration

Status: Draft; blocked by task, approval, permission, and sequencing decisions.

## 1. Goal

Implement approved project/course tasks, bounded subtasks, assignments,
dependencies, recurrence, task approvals, comments, tags, files, and complete
history without implementing progress formulas.

## 2. Included Features

- Task create, list/filter, detail, edit, archive/restore.
- Exactly one approved owner context: project or course.
- Subtasks up to the approved maximum depth.
- Assignees, watchers if approved, dates, status, priority, dependencies, and
  recurrence.
- Approved task completion/approval workflow.
- Comments, mentions metadata needed later, tags, files, and status/history.
- Arabic/English content and complete RTL/LTR task workflows.

## 3. Excluded Features

- Task/course/project progress calculation.
- Milestone or project-completion approval workflows.
- Notification delivery, dashboards, Kanban, calendar, Gantt, and reports.
- Any status, recurrence, dependency, or approval behavior not approved.

## 4. User Stories

- As an authorized manager, I can create and organize tasks in a permitted
  project/course.
- As an approved assignee, I can view/update the allowed task fields.
- As a collaborator, I can comment, tag, and attach approved files.
- As an approver, I can perform only the approved task-approval transitions.
- As an Arabic-speaking user, I can complete the full workflow in RTL without
  loss of Arabic task/comment text.

## 5. Models Involved

- `tasks.Task`, `TaskAssignment`, `TaskDependency`, `TaskRecurrence`.
- `TaskComment`, `Tag`, task-tag relationship, task file relationship.
- `TaskHistory`.
- Task approval models in `tasks` or reusable `approvals` primitives, pending
  the sequencing decision recorded in `IMPLEMENTATION_PLAN.md`.

## 6. Pages Involved

- Task list/filter, create, detail, edit, archive/restore.
- Subtask, assignment, dependency, recurrence, approval, comments, tags,
  files, and history sections.

## 7. Permission Requirements

The action matrix must distinguish task create/view/update/archive/approve,
assignment, comments, files, and history for project/course contexts.
Querysets inherit approved owner access and prevent cross-project/course
object references.

## 8. Validation Rules

- A task has exactly one supported owner and an accessible parent context.
- Parent chains are acyclic and within approved depth.
- Dependencies are valid, non-self-referential, and follow approved cycle/
  cross-context rules.
- Status transitions, completion, dates, recurrence, assignments, and approval
  behavior follow approved rules.
- Arabic text is preserved; search normalization never replaces source text.
- Comments/tags/files enforce size, content, and authorization limits.

## 9. Business Rules

- Resolve `BR-01`, `BR-02`, `BR-08`, `BR-10`, `BR-14`, `BR-16`, and all
  task permissions before approval.
- Progress and cancelled-denominator behavior remain deferred to Phase 6.
- Important tasks/comments/history use approved archive/delete behavior.

## 10. Expected Migrations

- Initial task, assignment, dependency, recurrence, comment, tag, file, and
  history models.
- Approved task-approval model/primitives.
- Check/unique constraints and indexes for owner, parent, assignee, status,
  priority, dates, archive, and dependency reads.

## 11. Unit Tests

- Task forms and owner/parent validation.
- Nesting-depth and cycle detection.
- Dependency, recurrence, transition, assignment, and approval policy.
- Comment/tag/file validation and localized labels/errors.

## 12. Integration Tests

- Authorized task lifecycle in projects and courses.
- Cross-context/object denial and form tampering.
- Concurrency/transactions for approval or multi-record changes.
- History completeness, constraints, and list/detail query counts.
- Arabic content/filter round-trip.

## 13. Browser Tests

- Create, assign, update, comment on, approve as allowed, and archive a task.
- Build subtasks/dependencies up to approved boundaries and see useful errors.
- Run the primary workflow in Arabic RTL and representative English LTR.

## 14. Security Tests

- Unauthorized assignment/status/approval changes.
- Cross-project/course IDs, direct URLs, restricted comments/history/files.
- CSRF/method safety, upload validation, and stored content escaping/
  bidirectional isolation.

## 15. Manual Verification

- Exercise task lifecycle for each relevant role.
- Verify depth, dependency, recurrence, approval, history, files, and archive.
- Review Arabic terminology, long titles/comments, mixed identifiers, RTL
  tables/forms, and localized validation.

## 16. Acceptance Criteria

- Approved task/subtask/assignment/dependency/recurrence behavior is enforced.
- Task approvals and history are transactional, authorized, and auditable.
- Project/course object access is preserved for every related record.
- Arabic/English task workflows and data pass localization verification.
- No progress, milestone approvals, notifications, or operational views are
  implemented.

## 17. Dependencies

- Completed Phases 3 and 4.
- Approved task statuses/transitions, nesting, dependency, recurrence,
  approval, dates, archive, file, and permission rules.
- Approved Arabic terminology and normalization policy.
- Owner decision on task-approval primitives versus Phase 7 sequencing.

## 18. Rollback Considerations

- Preserve task history/comments/files and approval evidence.
- Hierarchy/dependency constraint changes require preflight validation and
  staged migration.
- Recurrence or approval rollback must not duplicate tasks or erase decisions.
