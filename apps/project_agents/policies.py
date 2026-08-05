"""Phase 17 permissions layered on current project and domain authority."""

from django.conf import settings

from apps.accounts.models import User
from apps.project_agents.models import AgentProposal, AgentRun
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to


def _project_visible(actor: User, project: Project) -> bool:
    return (
        actor.is_active
        and projects_visible_to(actor, include_archived=True)
        .filter(pk=project.pk)
        .exists()
    )


def can_start_agent(actor: User, project: Project) -> bool:
    return (
        bool(settings.PROJECT_AGENT_ENABLED)
        and actor.has_perm("project_agents.start_agentrun")
        and not project.is_archived
        and _project_visible(actor, project)
    )


def can_view_agent_run(actor: User, run: AgentRun) -> bool:
    return actor.has_perm("project_agents.view_agentrun") and _project_visible(
        actor, run.project
    )


def can_review_agent_run(actor: User, run: AgentRun) -> bool:
    return (
        run.status == AgentRun.Status.COMPLETED
        and run.reviewed_at is None
        and actor.has_perm("project_agents.review_agentrun")
        and can_view_agent_run(actor, run)
    )


def can_decide_agent_proposal(actor: User, proposal: AgentProposal) -> bool:
    return (
        proposal.status == AgentProposal.Status.PENDING
        and actor.has_perm("project_agents.approve_agentproposal")
        and can_view_agent_run(actor, proposal.run)
    )


def can_execute_agent_proposal(actor: User, proposal: AgentProposal) -> bool:
    return (
        proposal.status
        in (AgentProposal.Status.APPROVED, AgentProposal.Status.EXECUTING)
        and proposal.approver_id == actor.pk
        and actor.has_perm("project_agents.execute_agentproposal")
        and can_view_agent_run(actor, proposal.run)
    )
