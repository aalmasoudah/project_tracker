"""Permission-scoped Phase 9 reads and constant-time token resolution."""

import hashlib

from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.attendance.models import Session, TrainerLink
from apps.courses.models import Course


def sessions_visible_to(
    actor: User, *, include_archived: bool = False
) -> QuerySet[Session]:
    queryset = Session.objects.select_related("course__project", "trainer")
    if actor.has_perm("attendance.manage_all_sessions"):
        visible = queryset
    elif actor.has_perm("attendance.manage_managed_sessions"):
        visible = queryset.filter(course__project__manager=actor)
    elif actor.has_perm("attendance.view_context_sessions"):
        visible = queryset.filter(
            Q(course__project__supervisor=actor),
            course__project__status="active",
            course__project__is_archived=False,
            course__status=Course.Status.ACTIVE,
            course__is_archived=False,
        )
    else:
        visible = queryset.none()
    if not include_archived or actor.has_perm("attendance.view_context_sessions"):
        visible = visible.filter(is_archived=False)
    return visible.distinct().order_by("start_at", "pk")


def visible_session_or_404(actor: User, session_id: int) -> Session:
    try:
        return sessions_visible_to(actor, include_archived=True).get(pk=session_id)
    except Session.DoesNotExist as error:
        raise Http404 from error


def can_manage_session(actor: User, session: Session | None = None) -> bool:
    if actor.has_perm("attendance.manage_all_sessions"):
        return session is None or (
            not session.course.is_archived and not session.course.project.is_archived
        )
    if not actor.has_perm("attendance.manage_managed_sessions"):
        return False
    return session is None or (
        session.course.project.manager_id == actor.pk
        and not session.course.is_archived
        and not session.course.project.is_archived
    )


def resolve_token(token: str) -> TrainerLink | None:
    if len(token) < 40 or len(token) > 100:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        return (
            TrainerLink.objects.select_related("session__course", "session__trainer")
            .prefetch_related(
                "session__participants__enrollment__trainee",
            )
            .get(token_hash=token_hash)
        )
    except TrainerLink.DoesNotExist:
        return None
