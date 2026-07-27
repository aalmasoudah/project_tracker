# Decision 0010: Phase 5 Tasks and Collaboration

- Status: Accepted
- Date: 2026-07-27
- Owner: Project owner

## Decision

- A task belongs to exactly one project or course. Its owner context is
  immutable. A subtask shares its parent's owner context.
- Hierarchy is acyclic and limited to three levels: root, child, grandchild.
- Statuses are `todo`, `in_progress`, `blocked`, `completed`, and `cancelled`.
  To Do may become In Progress or Cancelled; In Progress may become Blocked,
  Completed, or Cancelled; Blocked may become In Progress or Cancelled;
  Completed may reopen to In Progress; Cancelled may reopen to To Do.
- Priorities reuse Low, Medium, High, and Critical.
- Start and due dates are optional Gregorian date-only values with Western
  digits. Due cannot precede start and task dates must fit the owner context.
  Overdue calculation is deferred.
- Estimated and actual hours are optional non-negative values with two decimal
  places. Actual hours may exceed estimated hours and neither affects progress
  in this phase.
- A Blocked task requires a blocking reason.
- Tasks have multiple eligible assignees and exactly one active primary owner.
  The primary owner must be an assignee.
- CEO reads all tasks. Executive Manager manages all. Project Manager manages
  tasks in managed contexts. Supervisor sees tasks in approved active project
  contexts. Employee and Contractor see assigned tasks. Assignees may update
  status, actual hours, and blocking reason. Technical Admin has no access.
- Authorized visible collaborators may add immutable comments and private
  validated attachments. Managers maintain and select bilingual tags.
- Tasks, tags, assignments, and task-tag links are archived or end-dated.
  Comments, files, and history are not deleted through application paths.
- Task actions use a dedicated append-only audit scope.
- Arabic content is preserved and search uses the approved conservative
  normalization.
- Dependencies, recurrence, approvals, watchers, notifications, and all
  progress calculations are deferred. This resolves the Phase 5/Phase 7
  sequencing conflict in favor of the smaller original development plan.
