"""Permission-safe Phase 17 query helpers."""

from uuid import UUID

from django.http import Http404

from apps.accounts.models import User
from apps.project_agents.models import AgentProposal, AgentRun
from apps.project_agents.policies import can_view_agent_run


def visible_agent_run_or_404(actor: User, run_id: UUID | str) -> AgentRun:
    try:
        run = (
            AgentRun.objects.select_related("project", "requester", "reviewed_by")
            .prefetch_related("steps", "proposals__approver")
            .get(pk=run_id)
        )
    except (AgentRun.DoesNotExist, ValueError) as error:
        raise Http404 from error
    if not can_view_agent_run(actor, run):
        raise Http404
    return run


def visible_agent_proposal_or_404(
    actor: User, proposal_id: UUID | str
) -> AgentProposal:
    try:
        proposal = AgentProposal.objects.select_related(
            "run", "run__project", "run__requester", "approver"
        ).get(pk=proposal_id)
    except (AgentProposal.DoesNotExist, ValueError) as error:
        raise Http404 from error
    if not can_view_agent_run(actor, proposal.run):
        raise Http404
    return proposal
