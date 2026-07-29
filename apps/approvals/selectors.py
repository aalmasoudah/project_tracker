"""Permission-scoped milestone and approval selectors."""

from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.approvals.models import ApprovalRequest, Milestone
from apps.projects.models import Project


def milestones_visible_to(
    actor: User,
    *,
    search: str = "",
    include_archived: bool = False,
) -> QuerySet[Milestone]:
    queryset = Milestone.objects.select_related(
        "project",
        "project__manager",
        "project__supervisor",
    )
    if actor.has_perm("approvals.view_all_milestones"):
        visible = queryset
    elif actor.has_perm("approvals.view_managed_milestones"):
        visible = queryset.filter(project__manager=actor)
    elif actor.has_perm("approvals.view_context_milestones"):
        visible = queryset.filter(
            Q(project__supervisor=actor)
            | Q(
                project__memberships__user=actor,
                project__memberships__removed_at__isnull=True,
            ),
            project__status=Project.Status.ACTIVE,
            project__is_archived=False,
            is_archived=False,
        )
    else:
        visible = queryset.none()
    if not include_archived or actor.has_perm("approvals.view_context_milestones"):
        visible = visible.filter(is_archived=False)
    normalized = normalize_account_search(search)
    if normalized:
        visible = visible.filter(search_key__contains=normalized)
    return visible.distinct().order_by("project__code", "due_date", "code")


def visible_milestone_or_404(actor: User, milestone_id: int) -> Milestone:
    try:
        return milestones_visible_to(actor, include_archived=True).get(pk=milestone_id)
    except Milestone.DoesNotExist as error:
        raise Http404 from error


def can_manage_milestone(actor: User, milestone: Milestone) -> bool:
    if (
        milestone.is_archived
        or milestone.status
        in (Milestone.Status.PENDING_APPROVAL, Milestone.Status.COMPLETED)
        or not actor.has_perm("approvals.change_milestone")
    ):
        return False
    return (
        actor.has_perm("approvals.view_all_milestones")
        or milestone.project.manager_id == actor.pk
    )


def can_archive_milestone(actor: User, milestone: Milestone) -> bool:
    if not (
        actor.has_perm("approvals.archive_milestone")
        and actor.has_perm("approvals.restore_milestone")
    ):
        return False
    return (
        actor.has_perm("approvals.view_all_milestones")
        or milestone.project.manager_id == actor.pk
    )


def _request_queryset() -> QuerySet[ApprovalRequest]:
    return ApprovalRequest.objects.select_related(
        "submitted_by",
        "task",
        "task__project",
        "task__course",
        "task__course__project",
        "course",
        "course__project",
        "milestone",
        "milestone__project",
        "project",
    ).prefetch_related("steps__approver", "steps__decision__actor")


def _managed_target_q(actor: User) -> Q:
    return (
        Q(task__project__manager=actor)
        | Q(task__course__project__manager=actor)
        | Q(course__project__manager=actor)
        | Q(milestone__project__manager=actor)
        | Q(project__manager=actor)
    )


def _context_target_q(actor: User) -> Q:
    return (
        Q(task__project__supervisor=actor)
        | Q(task__course__project__supervisor=actor)
        | Q(course__project__supervisor=actor)
        | Q(milestone__project__supervisor=actor)
        | Q(project__supervisor=actor)
    )


def _active_context_q() -> Q:
    return (
        Q(
            task__project__status=Project.Status.ACTIVE,
            task__project__is_archived=False,
        )
        | Q(
            task__course__status="active",
            task__course__is_archived=False,
            task__course__project__status=Project.Status.ACTIVE,
            task__course__project__is_archived=False,
        )
        | Q(
            course__status="active",
            course__is_archived=False,
            course__project__status=Project.Status.ACTIVE,
            course__project__is_archived=False,
        )
        | Q(
            milestone__project__status=Project.Status.ACTIVE,
            milestone__project__is_archived=False,
            milestone__is_archived=False,
        )
        | Q(
            project__status=Project.Status.ACTIVE,
            project__is_archived=False,
        )
    )


def approval_requests_visible_to(actor: User) -> QuerySet[ApprovalRequest]:
    queryset = _request_queryset()
    if actor.has_perm("approvals.view_all_approvals"):
        visible = queryset
    elif actor.has_perm("approvals.view_managed_approvals"):
        visible = queryset.filter(_managed_target_q(actor))
    elif actor.has_perm("approvals.view_context_approvals"):
        visible = queryset.filter(_context_target_q(actor)).filter(_active_context_q())
    elif actor.has_perm("approvals.view_own_approvals"):
        visible = queryset.filter(submitted_by=actor)
    else:
        visible = queryset.none()
    return visible.distinct().order_by("-submitted_at", "-pk")


def visible_approval_request_or_404(
    actor: User,
    request_id: int,
) -> ApprovalRequest:
    try:
        return approval_requests_visible_to(actor).get(pk=request_id)
    except ApprovalRequest.DoesNotExist as error:
        raise Http404 from error
