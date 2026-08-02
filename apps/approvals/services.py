"""Transactional Phase 7 milestone and completion-approval workflows."""

from typing import cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.models import Max, Q
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.approvals.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStep,
    Milestone,
)
from apps.approvals.policies import (
    MILESTONE_STATUS_TRANSITIONS,
    PENDING_APPROVAL_STATUSES,
)
from apps.approvals.selectors import can_archive_milestone, can_manage_milestone
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.courses.models import Course
from apps.progress.calculations import HUNDRED, ProgressState
from apps.progress.services import (
    calculate_course_progress,
    calculate_project_progress,
    calculate_task_progress,
)
from apps.projects.models import Project
from apps.tasks.models import Task

type ApprovalTarget = Task | Course | Milestone | Project


def target_project(target: ApprovalTarget) -> Project:
    if isinstance(target, Project):
        return target
    if isinstance(target, Course):
        return target.project
    if isinstance(target, Milestone):
        return target.project
    if target.project_id:
        project = target.project
        assert project is not None
        return project
    course = target.course
    assert course is not None
    return course.project


def _target_type(target: ApprovalTarget) -> str:
    if isinstance(target, Task):
        return ApprovalRequest.TargetType.TASK
    if isinstance(target, Course):
        return ApprovalRequest.TargetType.COURSE
    if isinstance(target, Milestone):
        return ApprovalRequest.TargetType.MILESTONE
    return ApprovalRequest.TargetType.PROJECT


def _target_filter(target: ApprovalTarget) -> Q:
    if isinstance(target, Task):
        return Q(task=target)
    if isinstance(target, Course):
        return Q(course=target)
    if isinstance(target, Milestone):
        return Q(milestone=target)
    return Q(project=target)


def _target_kwargs(target: ApprovalTarget) -> dict[str, models.Model]:
    return {_target_type(target): target}


def _lock_target(target: ApprovalTarget) -> ApprovalTarget:
    return type(target).objects.select_for_update().get(pk=target.pk)


def has_pending_approval(target: ApprovalTarget) -> bool:
    return ApprovalRequest.objects.filter(
        _target_filter(target),
        status__in=PENDING_APPROVAL_STATUSES,
    ).exists()


def _record_event(
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: int,
    target_label: str,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        target_label=target_label,
        metadata=metadata,
        request=request,
        scope=AuditEvent.Scope.APPROVALS,
    )


def _validate_milestone(milestone: Milestone) -> None:
    if milestone.project.is_archived:
        raise ValidationError(_("Archived projects cannot own milestones."))
    if milestone.project.status in (
        Project.Status.CANCELLED,
        Project.Status.COMPLETED,
    ):
        raise ValidationError(_("This project cannot contain editable milestones."))
    milestone.full_clean()


@transaction.atomic
def create_milestone(
    *,
    actor: User,
    request: HttpRequest | None = None,
    **data: object,
) -> Milestone:
    if not actor.has_perm("approvals.add_milestone"):
        raise PermissionDenied(_("Milestone creation permission is required."))
    raw_code = data.get("code")
    if isinstance(raw_code, str):
        data["code"] = raw_code.strip().upper()
    milestone = Milestone(**data, created_by=actor, updated_by=actor)
    if not (
        actor.has_perm("approvals.view_all_milestones")
        or milestone.project.manager_id == actor.pk
    ):
        raise PermissionDenied(_("Milestones may be created only in managed projects."))
    if milestone.status != Milestone.Status.DRAFT:
        raise ValidationError(_("New milestones must start as Draft."))
    _validate_milestone(milestone)
    milestone.save()
    _record_event(
        actor=actor,
        action=actions.MILESTONE_CREATED,
        target_type="milestone",
        target_id=milestone.pk,
        target_label=milestone.code,
        request=request,
    )
    return milestone


@transaction.atomic
def update_milestone(
    *,
    actor: User,
    milestone: Milestone,
    request: HttpRequest | None = None,
    **data: object,
) -> Milestone:
    milestone = (
        Milestone.objects.select_for_update()
        .select_related("project")
        .get(pk=milestone.pk)
    )
    if not can_manage_milestone(actor, milestone):
        raise PermissionDenied(_("Milestone update permission is required."))
    if has_pending_approval(milestone):
        raise ValidationError(_("Pending approval prevents milestone changes."))
    previous_status = milestone.status
    if data.get("code") != milestone.code or data.get("project") != milestone.project:
        raise ValidationError(_("Milestone code and project cannot be changed."))
    for field_name, value in data.items():
        setattr(milestone, field_name, value)
    if (
        milestone.status != previous_status
        and milestone.status not in MILESTONE_STATUS_TRANSITIONS[previous_status]
    ):
        raise ValidationError(_("This milestone status transition is not allowed."))
    milestone.updated_by = actor
    _validate_milestone(milestone)
    milestone.save()
    _record_event(
        actor=actor,
        action=actions.MILESTONE_UPDATED,
        target_type="milestone",
        target_id=milestone.pk,
        target_label=milestone.code,
        metadata={"previous_status": previous_status, "status": milestone.status},
        request=request,
    )
    return milestone


@transaction.atomic
def archive_milestone(
    *,
    actor: User,
    milestone: Milestone,
    request: HttpRequest | None = None,
) -> Milestone:
    milestone = (
        Milestone.objects.select_for_update()
        .select_related("project")
        .get(pk=milestone.pk)
    )
    if not can_archive_milestone(actor, milestone):
        raise PermissionDenied(_("Milestone archive permission is required."))
    if milestone.is_archived:
        return milestone
    if has_pending_approval(milestone):
        raise ValidationError(_("Pending approval prevents milestone archiving."))
    milestone.is_archived = True
    milestone.archived_at = timezone.now()
    milestone.archived_by = actor
    milestone.updated_by = actor
    milestone.save(
        update_fields=(
            "is_archived",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        )
    )
    _record_event(
        actor=actor,
        action=actions.MILESTONE_ARCHIVED,
        target_type="milestone",
        target_id=milestone.pk,
        target_label=milestone.code,
        request=request,
    )
    return milestone


@transaction.atomic
def restore_milestone(
    *,
    actor: User,
    milestone: Milestone,
    request: HttpRequest | None = None,
) -> Milestone:
    milestone = (
        Milestone.objects.select_for_update()
        .select_related("project")
        .get(pk=milestone.pk)
    )
    if not can_archive_milestone(actor, milestone):
        raise PermissionDenied(_("Milestone restore permission is required."))
    if not milestone.is_archived:
        return milestone
    milestone.is_archived = False
    milestone.archived_at = None
    milestone.archived_by = None
    milestone.updated_by = actor
    _validate_milestone(milestone)
    milestone.save(
        update_fields=(
            "is_archived",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        )
    )
    _record_event(
        actor=actor,
        action=actions.MILESTONE_RESTORED,
        target_type="milestone",
        target_id=milestone.pk,
        target_label=milestone.code,
        request=request,
    )
    return milestone


def _can_submit(actor: User, target: ApprovalTarget) -> bool:
    if not actor.has_perm("approvals.submit_approval"):
        return False
    project = target_project(target)
    if actor.has_perm("approvals.view_all_approvals"):
        return True
    if project.manager_id == actor.pk:
        return True
    if isinstance(target, Task):
        return target.assignments.filter(
            user=actor,
            is_primary=True,
            removed_at__isnull=True,
        ).exists()
    return False


def _validate_submission_target(target: ApprovalTarget) -> None:
    project = target_project(target)
    if project.is_archived or project.status == Project.Status.CANCELLED:
        raise ValidationError(_("The target project is not eligible for approval."))
    if project.supervisor_id is None:
        raise ValidationError(_("Assign a project Supervisor before submission."))
    supervisor = project.supervisor
    assert supervisor is not None
    if not supervisor.is_active or not project.manager.is_active:
        raise ValidationError(_("Both approvers must be active."))
    if getattr(target, "is_archived", False):
        raise ValidationError(_("Archived records cannot be submitted."))
    if isinstance(target, Milestone):
        if target.status != Milestone.Status.IN_PROGRESS:
            raise ValidationError(_("Only an In Progress milestone can be submitted."))
        return
    if isinstance(target, Task):
        progress = calculate_task_progress(target)
        eligible_status = target.status == Task.Status.COMPLETED
    elif isinstance(target, Course):
        progress = calculate_course_progress(target)
        eligible_status = target.status == Course.Status.ACTIVE
    else:
        progress = calculate_project_progress(target)
        eligible_status = target.status == Project.Status.ACTIVE
    if (
        not eligible_status
        or progress.state != ProgressState.VALUE
        or progress.percentage != HUNDRED
    ):
        raise ValidationError(_("Completion submission requires 100 percent progress."))


@transaction.atomic
def submit_completion(
    *,
    actor: User,
    target: ApprovalTarget,
    request: HttpRequest | None = None,
) -> ApprovalRequest:
    target = _lock_target(target)
    if not _can_submit(actor, target):
        raise PermissionDenied(_("Completion submission permission is required."))
    if has_pending_approval(target):
        raise ValidationError(_("A completion approval is already pending."))
    _validate_submission_target(target)
    project = target_project(target)
    supervisor = project.supervisor
    assert supervisor is not None
    latest_attempt = (
        ApprovalRequest.objects.filter(_target_filter(target)).aggregate(
            maximum=Max("attempt")
        )["maximum"]
        or 0
    )
    approval_request = ApprovalRequest.objects.create(
        target_type=_target_type(target),
        attempt=latest_attempt + 1,
        status=ApprovalRequest.Status.PENDING_SUPERVISOR,
        submitted_by=actor,
        **_target_kwargs(target),
    )
    steps = (
        ApprovalStep(
            request=approval_request,
            sequence=1,
            role=ApprovalStep.Role.SUPERVISOR,
            approver=supervisor,
            status=ApprovalStep.Status.PENDING,
        ),
        ApprovalStep(
            request=approval_request,
            sequence=2,
            role=ApprovalStep.Role.PROJECT_MANAGER,
            approver=project.manager,
            status=ApprovalStep.Status.WAITING,
        ),
    )
    ApprovalStep.objects.bulk_create(steps)
    if isinstance(target, Milestone):
        target.status = Milestone.Status.PENDING_APPROVAL
        target.updated_by = actor
        target.save(update_fields=("status", "updated_by", "updated_at"))
    _record_event(
        actor=actor,
        action=actions.APPROVAL_SUBMITTED,
        target_type="approval_request",
        target_id=approval_request.pk,
        target_label=str(approval_request),
        metadata={
            "target_type": approval_request.target_type,
            "target_id": target.pk,
            "attempt": approval_request.attempt,
        },
        request=request,
    )
    from apps.notifications.events import notify_approval_action

    notify_approval_action(approval_request, steps[0])
    return approval_request


def _current_step(approval_request: ApprovalRequest) -> ApprovalStep:
    expected_sequence = (
        1
        if approval_request.status == ApprovalRequest.Status.PENDING_SUPERVISOR
        else 2
        if approval_request.status == ApprovalRequest.Status.PENDING_MANAGER
        else 0
    )
    if not expected_sequence:
        raise ValidationError(_("This approval request is already resolved."))
    return ApprovalStep.objects.select_for_update().get(
        request=approval_request,
        sequence=expected_sequence,
    )


def _authorize_decision(actor: User, step: ApprovalStep) -> None:
    required_permission = (
        "approvals.decide_supervisor_approval"
        if step.role == ApprovalStep.Role.SUPERVISOR
        else "approvals.decide_manager_approval"
    )
    if step.approver_id != actor.pk or not actor.has_perm(required_permission):
        raise PermissionDenied(_("You are not the assigned approver for this step."))
    if step.status != ApprovalStep.Status.PENDING:
        raise ValidationError(_("Only the current pending step can be decided."))


def _complete_target(target: ApprovalTarget, actor: User) -> None:
    if isinstance(target, Task):
        if target.status != Task.Status.COMPLETED:
            raise ValidationError(
                _("The completed task state changed during approval.")
            )
    elif isinstance(target, Course):
        target.status = Course.Status.COMPLETED
        target.updated_by = actor
        target.save(update_fields=("status", "updated_by", "updated_at"))
    elif isinstance(target, Milestone):
        target.status = Milestone.Status.COMPLETED
        target.updated_by = actor
        target.save(update_fields=("status", "updated_by", "updated_at"))
    else:
        target.status = Project.Status.COMPLETED
        target.updated_by = actor
        target.save(update_fields=("status", "updated_by", "updated_at"))


def _reject_target(target: ApprovalTarget, actor: User) -> None:
    if isinstance(target, Task):
        target.status = Task.Status.IN_PROGRESS
    elif isinstance(target, Course):
        target.status = Course.Status.ACTIVE
    elif isinstance(target, Milestone):
        target.status = Milestone.Status.IN_PROGRESS
    else:
        target.status = Project.Status.ACTIVE
    target.updated_by = actor
    target.save(update_fields=("status", "updated_by", "updated_at"))


@transaction.atomic
def approve_request(
    *,
    actor: User,
    approval_request: ApprovalRequest,
    request: HttpRequest | None = None,
) -> ApprovalRequest:
    approval_request = ApprovalRequest.objects.select_for_update().get(
        pk=approval_request.pk
    )
    step = _current_step(approval_request)
    _authorize_decision(actor, step)
    target = _lock_target(cast("ApprovalTarget", approval_request.target))
    now = timezone.now()
    ApprovalDecision.objects.create(
        step=step,
        actor=actor,
        outcome=ApprovalDecision.Outcome.APPROVED,
    )
    step.status = ApprovalStep.Status.APPROVED
    step.decided_at = now
    step.save(update_fields=("status", "decided_at"))
    if step.sequence == 1:
        next_step = ApprovalStep.objects.select_for_update().get(
            request=approval_request,
            sequence=2,
        )
        next_step.status = ApprovalStep.Status.PENDING
        next_step.save(update_fields=("status",))
        approval_request.status = ApprovalRequest.Status.PENDING_MANAGER
        approval_request.save(update_fields=("status",))
        from apps.notifications.events import notify_approval_action

        notify_approval_action(approval_request, next_step)
    else:
        _complete_target(target, actor)
        approval_request.status = ApprovalRequest.Status.APPROVED
        approval_request.resolved_at = now
        approval_request.save(update_fields=("status", "resolved_at"))
        from apps.notifications.events import notify_approval_updated

        notify_approval_updated(
            approval_request,
            event="approved",
            actor=actor,
        )
    _record_event(
        actor=actor,
        action=actions.APPROVAL_APPROVED,
        target_type="approval_request",
        target_id=approval_request.pk,
        target_label=str(approval_request),
        metadata={"sequence": step.sequence, "attempt": approval_request.attempt},
        request=request,
    )
    return approval_request


@transaction.atomic
def reject_request(
    *,
    actor: User,
    approval_request: ApprovalRequest,
    reason: str,
    request: HttpRequest | None = None,
) -> ApprovalRequest:
    reason = reason.strip()
    if not reason:
        raise ValidationError(_("A rejection reason is required."))
    approval_request = ApprovalRequest.objects.select_for_update().get(
        pk=approval_request.pk
    )
    step = _current_step(approval_request)
    _authorize_decision(actor, step)
    target = _lock_target(cast("ApprovalTarget", approval_request.target))
    now = timezone.now()
    ApprovalDecision.objects.create(
        step=step,
        actor=actor,
        outcome=ApprovalDecision.Outcome.REJECTED,
        reason=reason,
    )
    step.status = ApprovalStep.Status.REJECTED
    step.decided_at = now
    step.save(update_fields=("status", "decided_at"))
    _reject_target(target, actor)
    approval_request.status = ApprovalRequest.Status.REJECTED
    approval_request.resolved_at = now
    approval_request.save(update_fields=("status", "resolved_at"))
    _record_event(
        actor=actor,
        action=actions.APPROVAL_REJECTED,
        target_type="approval_request",
        target_id=approval_request.pk,
        target_label=str(approval_request),
        metadata={"sequence": step.sequence, "attempt": approval_request.attempt},
        request=request,
    )
    from apps.notifications.events import notify_approval_updated

    notify_approval_updated(
        approval_request,
        event="rejected",
        actor=actor,
    )
    return approval_request
