"""Thin localized Phase 7 milestone and approval views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.approvals.forms import MilestoneForm, RejectionForm
from apps.approvals.models import ApprovalRequest, ApprovalStep
from apps.approvals.selectors import (
    approval_requests_visible_to,
    can_archive_milestone,
    can_manage_milestone,
    milestones_visible_to,
    visible_approval_request_or_404,
    visible_milestone_or_404,
)
from apps.approvals.services import (
    ApprovalTarget,
    approve_request,
    archive_milestone,
    create_milestone,
    reject_request,
    restore_milestone,
    submit_completion,
    update_milestone,
)
from apps.courses.selectors import visible_course_or_404
from apps.progress.services import milestone_progress_for
from apps.projects.selectors import visible_project_or_404
from apps.tasks.selectors import visible_task_or_404


@login_required
@permission_required("approvals.view_milestone", raise_exception=True)
def milestone_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    milestones = milestones_visible_to(
        actor,
        search=request.GET.get("q", ""),
        include_archived=request.GET.get("archived") == "1",
    )
    page = Paginator(milestones, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "approvals/milestone_list.html",
        {"page": page, "search": request.GET.get("q", "")},
    )


@login_required
@permission_required("approvals.view_milestone", raise_exception=True)
def milestone_detail(request: HttpRequest, milestone_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    milestone = visible_milestone_or_404(actor, milestone_id)
    requests = approval_requests_visible_to(actor).filter(milestone=milestone)
    return render(
        request,
        "approvals/milestone_detail.html",
        {
            "milestone": milestone,
            "progress": milestone_progress_for(actor, milestone),
            "approval_requests": requests,
            "can_manage": can_manage_milestone(actor, milestone),
            "can_archive": can_archive_milestone(actor, milestone),
            "can_submit": actor.has_perm("approvals.submit_approval"),
        },
    )


@login_required
@permission_required("approvals.add_milestone", raise_exception=True)
@require_http_methods(["GET", "POST"])
def milestone_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = MilestoneForm(request.POST or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            milestone = create_milestone(
                actor=actor,
                request=request,
                **form.cleaned_data,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Milestone created."))
            return redirect("approvals:milestone_detail", milestone.pk)
    return render(
        request,
        "approvals/milestone_form.html",
        {"form": form, "title": _("Create milestone")},
    )


@login_required
@permission_required("approvals.change_milestone", raise_exception=True)
@require_http_methods(["GET", "POST"])
def milestone_update(request: HttpRequest, milestone_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    milestone = visible_milestone_or_404(actor, milestone_id)
    if not can_manage_milestone(actor, milestone):
        raise PermissionDenied
    form = MilestoneForm(
        request.POST or None,
        actor=actor,
        instance=milestone,
    )
    if request.method == "POST" and form.is_valid():
        try:
            milestone = update_milestone(
                actor=actor,
                milestone=milestone,
                request=request,
                **form.cleaned_data,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Milestone updated."))
            return redirect("approvals:milestone_detail", milestone.pk)
    return render(
        request,
        "approvals/milestone_form.html",
        {"form": form, "title": _("Edit milestone")},
    )


def _archive_action(
    request: HttpRequest,
    milestone_id: int,
    *,
    restore: bool,
) -> HttpResponse:
    actor = cast(User, request.user)
    milestone = visible_milestone_or_404(actor, milestone_id)
    service = restore_milestone if restore else archive_milestone
    try:
        service(actor=actor, milestone=milestone, request=request)
    except (PermissionDenied, ValidationError) as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            _("Milestone restored.") if restore else _("Milestone archived."),
        )
    return redirect("approvals:milestone_detail", milestone.pk)


@login_required
@require_POST
def milestone_archive(request: HttpRequest, milestone_id: int) -> HttpResponse:
    return _archive_action(request, milestone_id, restore=False)


@login_required
@require_POST
def milestone_restore(request: HttpRequest, milestone_id: int) -> HttpResponse:
    return _archive_action(request, milestone_id, restore=True)


@login_required
@permission_required("approvals.view_approvalrequest", raise_exception=True)
def approval_queue(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    approvals = approval_requests_visible_to(actor)
    status = request.GET.get("status", "")
    if status in ApprovalRequest.Status.values:
        approvals = approvals.filter(status=status)
    page = Paginator(approvals, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "approvals/approval_queue.html",
        {
            "page": page,
            "statuses": ApprovalRequest.Status.choices,
            "selected_status": status,
        },
    )


def _pending_step(approval_request: ApprovalRequest) -> ApprovalStep | None:
    return next(
        (
            step
            for step in approval_request.steps.all()
            if step.status == ApprovalStep.Status.PENDING
        ),
        None,
    )


@login_required
@permission_required("approvals.view_approvalrequest", raise_exception=True)
def approval_detail(request: HttpRequest, request_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    approval_request = visible_approval_request_or_404(actor, request_id)
    current_step = _pending_step(approval_request)
    can_decide = bool(
        current_step
        and current_step.approver_id == actor.pk
        and (
            (
                current_step.role == ApprovalStep.Role.SUPERVISOR
                and actor.has_perm("approvals.decide_supervisor_approval")
            )
            or (
                current_step.role == ApprovalStep.Role.PROJECT_MANAGER
                and actor.has_perm("approvals.decide_manager_approval")
            )
        )
    )
    return render(
        request,
        "approvals/approval_detail.html",
        {
            "approval_request": approval_request,
            "current_step": current_step,
            "can_decide": can_decide,
        },
    )


def _visible_target(
    actor: User,
    target_type: str,
    target_id: int,
) -> ApprovalTarget:
    if target_type == ApprovalRequest.TargetType.TASK:
        return visible_task_or_404(actor, target_id)
    if target_type == ApprovalRequest.TargetType.COURSE:
        return visible_course_or_404(actor, target_id)
    if target_type == ApprovalRequest.TargetType.MILESTONE:
        return visible_milestone_or_404(actor, target_id)
    if target_type == ApprovalRequest.TargetType.PROJECT:
        return visible_project_or_404(actor, target_id)
    raise Http404


@login_required
@permission_required("approvals.submit_approval", raise_exception=True)
@require_http_methods(["GET", "POST"])
def approval_submit(
    request: HttpRequest,
    target_type: str,
    target_id: int,
) -> HttpResponse:
    actor = cast(User, request.user)
    target = _visible_target(actor, target_type, target_id)
    if request.method == "POST":
        try:
            approval_request = submit_completion(
                actor=actor,
                target=target,
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            messages.error(request, str(error))
        else:
            messages.success(request, _("Completion submitted for approval."))
            return redirect("approvals:detail", approval_request.pk)
    return render(
        request,
        "approvals/approval_submit.html",
        {"target": target, "target_type": target_type},
    )


@login_required
@permission_required("approvals.view_approvalrequest", raise_exception=True)
@require_POST
def approval_approve(request: HttpRequest, request_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    approval_request = visible_approval_request_or_404(actor, request_id)
    try:
        approve_request(
            actor=actor,
            approval_request=approval_request,
            request=request,
        )
    except (PermissionDenied, ValidationError) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Approval recorded."))
    return redirect("approvals:detail", approval_request.pk)


@login_required
@permission_required("approvals.view_approvalrequest", raise_exception=True)
@require_http_methods(["GET", "POST"])
def approval_reject(request: HttpRequest, request_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    approval_request = visible_approval_request_or_404(actor, request_id)
    form = RejectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reject_request(
                actor=actor,
                approval_request=approval_request,
                reason=form.cleaned_data["reason"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Rejection recorded."))
            return redirect("approvals:detail", approval_request.pk)
    return render(
        request,
        "approvals/approval_reject.html",
        {"form": form, "approval_request": approval_request},
    )
