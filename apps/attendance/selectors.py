"""Permission-scoped attendance reads and constant-time token resolution."""

import hashlib

from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.attendance.models import AttendanceSubmission, Session, TrainerLink
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


def submissions_visible_to(actor: User) -> QuerySet[AttendanceSubmission]:
    queryset = AttendanceSubmission.objects.select_related(
        "session__course__project",
        "session__trainer",
        "trainer_link",
    ).prefetch_related(
        "entries__participant__enrollment__trainee",
        "reviews__reviewer",
        "corrections__corrected_by",
    )
    if actor.has_perm("attendance.view_all_attendance"):
        visible = queryset
    elif actor.has_perm("attendance.view_managed_attendance"):
        visible = queryset.filter(session__course__project__manager=actor)
    elif actor.has_perm("attendance.view_supervised_attendance"):
        visible = queryset.filter(
            session__course__project__supervisor=actor,
            session__course__project__status="active",
            session__course__project__is_archived=False,
            session__course__status=Course.Status.ACTIVE,
            session__course__is_archived=False,
            session__is_archived=False,
        )
    else:
        visible = queryset.none()
    return visible.distinct().order_by("-submitted_at", "-pk")


def visible_submission_or_404(actor: User, submission_id: int) -> AttendanceSubmission:
    try:
        return submissions_visible_to(actor).get(pk=submission_id)
    except AttendanceSubmission.DoesNotExist as error:
        raise Http404 from error


def can_review_submission(actor: User, submission: AttendanceSubmission) -> bool:
    project = submission.session.course.project
    return (
        actor.is_active
        and actor.has_perm("attendance.review_attendance")
        and project.supervisor_id == actor.pk
        and project.status == "active"
        and not project.is_archived
        and submission.session.course.status == Course.Status.ACTIVE
        and not submission.session.course.is_archived
        and not submission.session.is_archived
    )


def can_correct_submission(actor: User, submission: AttendanceSubmission) -> bool:
    if not actor.is_active:
        return False
    if actor.has_perm("attendance.correct_all_attendance"):
        return True
    return (
        actor.has_perm("attendance.correct_managed_attendance")
        and submission.session.course.project.manager_id == actor.pk
    )


def pending_submissions_for(actor: User) -> QuerySet[AttendanceSubmission]:
    if not actor.has_perm("attendance.review_attendance"):
        return submissions_visible_to(actor).none()
    return submissions_visible_to(actor).filter(
        state=AttendanceSubmission.State.PENDING_REVIEW,
        session__course__project__supervisor=actor,
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
                "submission__entries__participant__enrollment__trainee",
                "submission__reviews",
            )
            .get(token_hash=token_hash)
        )
    except TrainerLink.DoesNotExist:
        return None
