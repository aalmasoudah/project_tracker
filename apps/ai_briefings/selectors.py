"""Permission-scoped briefing and citation selectors."""

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import Http404
from django.urls import reverse

from apps.accounts.models import User
from apps.ai_briefings.models import AIBriefing, AIBriefingSource
from apps.approvals.selectors import (
    approval_requests_visible_to,
    milestones_visible_to,
)
from apps.audit.selectors import audit_events_visible_to
from apps.projects.selectors import projects_visible_to
from apps.tasks.selectors import tasks_visible_to


def briefings_visible_to(actor: User) -> QuerySet[AIBriefing]:
    if not actor.is_active or not actor.has_perm("ai_briefings.view_aibriefing"):
        return AIBriefing.objects.none()
    return AIBriefing.objects.select_related(
        "project", "requested_by", "reviewed_by"
    ).filter(project__in=projects_visible_to(actor, include_archived=True))


def visible_briefing_or_404(actor: User, briefing_id: int) -> AIBriefing:
    try:
        return briefings_visible_to(actor).get(pk=briefing_id)
    except AIBriefing.DoesNotExist as error:
        raise Http404 from error


def source_url_for(actor: User, source: AIBriefingSource) -> str | None:
    """Return an internal URL only if the actor can currently open the source."""
    try:
        source_id = int(source.source_id)
    except ValueError:
        return None
    if source.source_type == AIBriefingSource.SourceType.PROJECT:
        if (
            projects_visible_to(actor, include_archived=True)
            .filter(pk=source_id)
            .exists()
        ):
            return reverse("projects:detail", args=(source_id,))
    elif source.source_type == AIBriefingSource.SourceType.TASK:
        if tasks_visible_to(actor, include_archived=True).filter(pk=source_id).exists():
            return reverse("tasks:detail", args=(source_id,))
    elif source.source_type == AIBriefingSource.SourceType.MILESTONE:
        if (
            milestones_visible_to(actor, include_archived=True)
            .filter(pk=source_id)
            .exists()
        ):
            return reverse("approvals:milestone_detail", args=(source_id,))
    elif source.source_type == AIBriefingSource.SourceType.APPROVAL:
        if approval_requests_visible_to(actor).filter(pk=source_id).exists():
            return reverse("approvals:detail", args=(source_id,))
    elif source.source_type == AIBriefingSource.SourceType.AUDIT:
        try:
            allowed = audit_events_visible_to(actor).filter(pk=source_id).exists()
        except PermissionDenied:
            allowed = False
        if allowed:
            return reverse("audit:detail", args=(source_id,))
    return None
