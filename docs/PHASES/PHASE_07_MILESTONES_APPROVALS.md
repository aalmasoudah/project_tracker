# Phase 7: Milestones and Approvals

Status: Draft; blocked by approval, progress, permission, and sequencing
decisions.

## 1. Goal

Implement milestones and transactional multi-step milestone/project
completion approvals with explicit states, rejection/history, and integration
with the centralized progress engine.

## 2. Included Features

- Milestone lifecycle under projects.
- Approved sequential/parallel approval steps and assigned approvers.
- Submit, approve, reject, reopen/resubmit, override, and completion behavior
  only as approved.
- Immutable decision history and audit events.
- Row locking/transactions for concurrent decisions.
- Approved milestone/project progress integration.
- Arabic/English approval queues, reasons, history, and RTL/LTR workflows.

## 3. Excluded Features

- Attendance approval, which belongs to Phase 10.
- Notification delivery, dashboards beyond bounded approval pages, and reports.
- Any inferred approval actor, step, transition, or override.

## 4. User Stories

- As an authorized manager, I can define/maintain approved milestones.
- As an authorized requester, I can submit eligible completion for approval.
- As an assigned approver, I can approve/reject the current permitted step.
- As an auditor, I can reconstruct decisions and reasons.
- As an Arabic-speaking approver, I can complete the workflow fully in RTL.

## 5. Models Involved

- `approvals.Milestone`, `ApprovalRequest`, `ApprovalStep`,
  `ApprovalDecision`, and explicit history/audit relationships.
- Project and approved user/group references.
- Existing centralized progress services.

The reusable approval primitives may begin in Phase 5 if that sequencing is
explicitly approved.

## 6. Pages Involved

- Milestone list/create/detail/edit/archive.
- Completion submission, approval queue/detail, approve/reject/reopen actions,
  and read-only history.

## 7. Permission Requirements

The matrix must name submitters, each approver class, reject/reopen/override
actors, audit viewers, and project-scope boundaries. An actor cannot approve
for another step or a project they cannot access.

## 8. Validation Rules

- Milestone dates/status/eligibility follow approved project rules.
- Only the current eligible step can transition.
- Required reasons are enforced for approved rejection/reopen/override paths.
- Duplicate/concurrent decisions are prevented transactionally.
- Completed requests and immutable decisions cannot be edited normally.
- Arabic reasons preserve source text and render with safe direction.

## 9. Business Rules

Resolve `BR-06`, `BR-08`, `BR-09`, `BR-10`, `BR-14`, `BR-16`, and approval
permissions. No unapproved transition is represented even if technically easy.

## 10. Expected Migrations

- Initial milestone and approval request/step/decision/history models, or
  extensions to approved Phase 5 primitives.
- State/sequence uniqueness and check constraints.
- Indexes for project, approver, state, submitted date, and active queues.

## 11. Unit Tests

- State machine and eligibility.
- Step ordering/parallel behavior as approved.
- Reject/reopen/override reason validation.
- Progress integration and localized labels/errors.

## 12. Integration Tests

- Full approval and rejection/resubmission lifecycles.
- Concurrent/duplicate decisions with row locking.
- Wrong actor/project/step denial.
- Immutable history/audit completeness and query counts.

## 13. Browser Tests

- Submit, approve through all steps, and complete.
- Reject with reason, reopen/resubmit as approved.
- Verify queues/history in Arabic RTL and English LTR.

## 14. Security Tests

- Direct URL and forged-step/actor/state attacks.
- Self-approval/override where prohibited.
- History/reason/project information leakage.
- CSRF, method safety, and concurrent replay.

## 15. Manual Verification

- Run every approved transition with fictional roles.
- Attempt invalid/out-of-order/concurrent actions.
- Compare progress before/after approval.
- Review Arabic terminology, reasons, history order, and mixed identifiers.

## 16. Acceptance Criteria

- Milestones and completion approvals match the approved state machine exactly.
- Transactions prevent conflicting decisions.
- All actors, object scopes, reasons, and overrides are authorized.
- History/audit is complete and normally immutable.
- Progress uses centralized services.
- Arabic/English approval workflows pass localization verification.

## 17. Dependencies

- Completed Phase 6 and approved milestone/progress availability.
- Approved approval steps, actors, transitions, self-approval, override,
  rejection/reopen, date, archive, and permission rules.
- Approved Arabic approval terminology.
- Owner resolution of Phase 5 task-approval and Phase 6 milestone sequencing.

## 18. Rollback Considerations

- Never erase decisions/history to roll back UI behavior.
- State-machine schema changes require mapping existing requests safely.
- A code rollback must understand states written by the newer version or the
  release must be paused for a controlled migration.
