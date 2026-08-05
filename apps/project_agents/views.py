"""Thin bilingual Phase 17 request, timeline, and decision views."""

from typing import cast
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.models import User
from apps.approvals.selectors import (
    approval_requests_visible_to,
    milestones_visible_to,
)
from apps.project_agents.forms import AgentRunRequestForm, ProposalDecisionForm
from apps.project_agents.models import AgentRun, AgentStep
from apps.project_agents.policies import (
    can_decide_agent_proposal,
    can_review_agent_run,
    can_start_agent,
)
from apps.project_agents.selectors import (
    visible_agent_proposal_or_404,
    visible_agent_run_or_404,
)
from apps.project_agents.services import (
    cancel_agent_run,
    decide_agent_proposal,
    request_agent_run,
    review_agent_run,
)
from apps.projects.selectors import visible_project_or_404
from apps.tasks.selectors import tasks_visible_to


def _source_map(actor: User, run: AgentRun) -> dict[str, dict[str, object]]:
    sources: dict[str, dict[str, object]] = {}
    visible_task_ids = set(tasks_visible_to(actor).values_list("pk", flat=True))
    visible_milestone_ids = set(
        milestones_visible_to(actor).values_list("pk", flat=True)
    )
    visible_approval_ids = set(
        approval_requests_visible_to(actor).values_list("pk", flat=True)
    )
    for call in run.tool_calls.filter(status="completed"):
        result = call.safe_result
        items = result.get("items", []) if isinstance(result, dict) else []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
                continue
            source_type = str(item.get("type", ""))
            raw_id = item.get("id")
            try:
                source_id = int(str(raw_id))
            except ValueError:
                source_id = 0
            allowed = (
                source_type in {"project", "progress", "team_member", "reviewed_memory"}
                or (source_type == "task" and source_id in visible_task_ids)
                or (source_type == "milestone" and source_id in visible_milestone_ids)
                or (source_type == "approval" and source_id in visible_approval_ids)
            )
            sources[str(item["ref"])] = {
                "label": str(item.get("label", item["ref"])),
                "url": str(item.get("path", "")) if allowed else "",
            }
    return sources


def _present_cited(
    items: object, sources: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    if not isinstance(items, list):
        return []
    result: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        citations = item.get("citations", [])
        links: list[dict[str, object]] = (
            [
                sources[ref]
                for ref in citations
                if isinstance(ref, str) and ref in sources
            ]
            if isinstance(citations, list)
            else []
        )
        result.append({"text": str(item.get("text", "")), "citations": links})
    return result


def _run_context(actor: User, run: AgentRun) -> dict[str, object]:
    run = visible_agent_run_or_404(actor, run.pk)
    sources = _source_map(actor, run)
    output = run.output_data if isinstance(run.output_data, dict) else {}
    steps = list(run.steps.order_by("sequence"))
    proposals = list(run.proposals.all())
    proposal_cards = [
        {
            "proposal": proposal,
            "can_decide": can_decide_agent_proposal(actor, proposal),
            "citations": [
                sources[reference]
                for reference in proposal.citations
                if isinstance(reference, str) and reference in sources
            ]
            if isinstance(proposal.citations, list)
            else [],
        }
        for proposal in proposals
    ]
    verification = (
        run.verification_data if isinstance(run.verification_data, dict) else {}
    )
    raw_verification_results = verification.get("results", [])
    verification_results = (
        [
            {
                "action_code": str(item.get("action_code", "")),
                "status": str(item.get("status", "")),
                "source": sources.get(str(item.get("citation", ""))),
            }
            for item in raw_verification_results
            if isinstance(item, dict)
        ]
        if isinstance(raw_verification_results, list)
        else []
    )
    return {
        "run": run,
        "steps": steps,
        "sources": sources,
        "findings": _present_cited(output.get("findings", []), sources),
        "recommendations": _present_cited(output.get("recommendations", []), sources),
        "summary": str(output.get("summary", "")),
        "can_review": can_review_agent_run(actor, run),
        "can_cancel": run.requester_id == actor.pk
        and run.status
        in {
            AgentRun.Status.QUEUED,
            AgentRun.Status.PLANNING,
            AgentRun.Status.RUNNING,
            AgentRun.Status.AWAITING_APPROVAL,
        },
        "decision_form": ProposalDecisionForm(),
        "poll": run.status
        in {
            AgentRun.Status.QUEUED,
            AgentRun.Status.PLANNING,
            AgentRun.Status.RUNNING,
            AgentRun.Status.EXECUTING,
            AgentRun.Status.VERIFYING,
        },
        "step_type": AgentStep.StepType,
        "proposal_cards": proposal_cards,
        "verification_summary": str(verification.get("summary", "")),
        "verification_results": verification_results,
    }


@login_required
@require_http_methods(["GET", "POST"])
def agent_request(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not can_start_agent(actor, project):
        raise PermissionDenied
    form = AgentRunRequestForm(request.POST or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            run = request_agent_run(
                actor=actor,
                project=project,
                goal_code=cast(str, form.cleaned_data["goal_code"]),
                optional_context=cast(str, form.cleaned_data["optional_context"]),
                language=cast(str, form.cleaned_data["language"]),
                model_code=cast(str, form.cleaned_data["model_code"]),
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Project-agent run queued."))
            return redirect("project_agents:detail", run_id=run.pk)
    return render(
        request, "project_agents/request.html", {"project": project, "form": form}
    )


@login_required
@require_GET
def agent_detail(request: HttpRequest, run_id: UUID) -> HttpResponse:
    actor = cast(User, request.user)
    run = visible_agent_run_or_404(actor, run_id)
    return render(request, "project_agents/detail.html", _run_context(actor, run))


@login_required
@require_GET
def agent_status(request: HttpRequest, run_id: UUID) -> HttpResponse:
    actor = cast(User, request.user)
    run = visible_agent_run_or_404(actor, run_id)
    return render(request, "project_agents/_status.html", _run_context(actor, run))


def _decision(
    request: HttpRequest, proposal_id: UUID, *, approve: bool
) -> HttpResponse:
    actor = cast(User, request.user)
    proposal = visible_agent_proposal_or_404(actor, proposal_id)
    form = ProposalDecisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("A valid decision reason is required."))
        return redirect("project_agents:detail", run_id=proposal.run_id)
    try:
        decided = decide_agent_proposal(
            actor=actor,
            proposal=proposal,
            approve=approve,
            reason=cast(str, form.cleaned_data["reason"]),
            request=request,
        )
    except ValidationError as error:
        messages.error(request, str(error))
        return redirect("project_agents:detail", run_id=proposal.run_id)
    if decided.status == decided.Status.EXPIRED:
        messages.error(request, _("This project-agent proposal has expired."))
        return redirect("project_agents:detail", run_id=proposal.run_id)
    messages.success(
        request,
        _("Proposal approved and queued for verified execution.")
        if approve
        else _("Proposal rejected."),
    )
    return redirect("project_agents:detail", run_id=proposal.run_id)


@login_required
@require_POST
def proposal_approve(request: HttpRequest, proposal_id: UUID) -> HttpResponse:
    return _decision(request, proposal_id, approve=True)


@login_required
@require_POST
def proposal_reject(request: HttpRequest, proposal_id: UUID) -> HttpResponse:
    return _decision(request, proposal_id, approve=False)


@login_required
@require_POST
def agent_review(request: HttpRequest, run_id: UUID) -> HttpResponse:
    actor = cast(User, request.user)
    run = visible_agent_run_or_404(actor, run_id)
    review_agent_run(actor=actor, run=run, request=request)
    messages.success(
        request, _("Project-agent run reviewed and added to project memory.")
    )
    return redirect("project_agents:detail", run_id=run.pk)


@login_required
@require_POST
def agent_cancel(request: HttpRequest, run_id: UUID) -> HttpResponse:
    actor = cast(User, request.user)
    run = visible_agent_run_or_404(actor, run_id)
    cancel_agent_run(actor=actor, run=run, request=request)
    messages.success(request, _("Project-agent run cancelled."))
    return redirect("project_agents:detail", run_id=run.pk)
