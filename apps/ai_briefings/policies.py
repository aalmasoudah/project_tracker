"""Phase 15 permission and object-scope policies."""

from django.conf import settings

from apps.accounts.models import User
from apps.ai_briefings.models import AIBriefing
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to


def can_generate_briefing(actor: User, project: Project) -> bool:
    return (
        bool(settings.AI_BRIEFING_ENABLED)
        and actor.is_active
        and actor.has_perm("ai_briefings.generate_aibriefing")
        and not project.is_archived
        and projects_visible_to(actor, include_archived=True)
        .filter(pk=project.pk)
        .exists()
    )


def can_view_briefing(actor: User, briefing: AIBriefing) -> bool:
    return (
        actor.is_active
        and actor.has_perm("ai_briefings.view_aibriefing")
        and projects_visible_to(actor, include_archived=True)
        .filter(pk=briefing.project_id)
        .exists()
    )


def can_review_briefing(actor: User, briefing: AIBriefing) -> bool:
    return (
        briefing.status == AIBriefing.Status.COMPLETED
        and briefing.reviewed_at is None
        and actor.has_perm("ai_briefings.review_aibriefing")
        and can_view_briefing(actor, briefing)
    )
