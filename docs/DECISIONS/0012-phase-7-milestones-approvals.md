# Decision 0012: Phase 7 Milestones and Approvals

Date: 2026-07-28

Status: Approved

## Context

Phase 7 introduces milestones and completion approvals for tasks, courses,
milestones, and projects. The original playbook specifies Supervisor then
Project Manager ordering and rejection back to active work, but leaves the
remaining transition, visibility, and progress details open.

## Decision

- Completion approval uses two strict sequential steps: the owning project's
  Supervisor first, then its Project Manager.
- The responsible task assignee or owning Project Manager may submit; an
  Executive Manager may submit in any context. A submitter may later perform
  their assigned approval step, but one actor cannot fill both approval steps.
- Rejection requires a reason. Rejected tasks and milestones return to In
  Progress; rejected courses and projects return to Active.
- Resubmission creates a new immutable approval attempt. Earlier requests,
  steps, decisions, actors, timestamps, and reasons remain unchanged.
- Phase 7 has no override path.
- Milestone statuses are Draft, In Progress, Pending Approval, Completed, and
  Cancelled. Completed milestones are 100 percent; other countable milestone
  statuses are 0 percent. Cancelled/archived milestones are excluded.
- Project progress adds milestones as another equally weighted available
  category.
- Tasks, courses, and projects require 100-percent centralized progress before
  submission. A milestone is the approved exception: it may submit directly
  from In Progress because approval is what makes its progress 100 percent.
- Executive Manager manages milestones globally; Project Manager manages
  milestones in owned projects. Supervisor and Project Manager decide only
  their assigned step.
- CEO and Executive Manager may read all approval history. Project Manager
  reads managed history, Supervisor reads visible-context history, and a
  submitter may read their own requests.
- Pending approval prevents normal editing and archiving of its target.
  Approval requests, steps, decisions, and history are never deleted.
- Milestone dates are Gregorian date-only values with Western digits and must
  remain within project dates. Phase 7 screens are fully Arabic/English and
  direction-aware.

## Consequences

Project and course gain an approval-only Completed status. Normal edit forms
cannot choose it. Milestone/project progress remains centralized. Phase 7
requires database migrations for milestone, request, step, decision, role
permissions, and project/course status choices.
