"""Permission-scoped Phase 4 query helpers."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.audit.models import AuditEvent
from apps.courses.models import Course, Trainer


def courses_visible_to(
    actor: User,
    *,
    search: str = "",
    status: str = "",
    include_archived: bool = False,
) -> QuerySet[Course]:
    """Return only courses the actor may discover."""
    queryset = Course.objects.select_related("project", "project__manager")
    if actor.has_perm("courses.view_all_courses"):
        visible = queryset
    elif actor.has_perm("courses.view_managed_courses"):
        visible = queryset.filter(project__manager=actor)
    elif actor.has_perm("courses.view_assigned_courses"):
        visible = queryset.filter(
            Q(project__supervisor=actor)
            | Q(
                project__memberships__user=actor,
                project__memberships__removed_at__isnull=True,
            ),
            project__is_archived=False,
            project__status="active",
            is_archived=False,
            status=Course.Status.ACTIVE,
        )
    else:
        visible = queryset.none()
    if not include_archived or actor.has_perm("courses.view_assigned_courses"):
        visible = visible.filter(is_archived=False)
    normalized = normalize_account_search(search)
    if normalized:
        visible = visible.filter(search_key__contains=normalized)
    if status in Course.Status.values:
        visible = visible.filter(status=status)
    return visible.distinct().order_by("code")


def visible_course_or_404(actor: User, course_id: int) -> Course:
    try:
        return courses_visible_to(actor, include_archived=True).get(pk=course_id)
    except Course.DoesNotExist as error:
        raise Http404 from error


def can_manage_course(actor: User, course: Course) -> bool:
    if (
        not actor.has_perm("courses.change_course")
        or course.is_archived
        or course.status == Course.Status.COMPLETED
    ):
        return False
    return (
        actor.has_perm("courses.view_all_courses")
        or course.project.manager_id == actor.pk
    )


def can_archive_course(actor: User, course: Course) -> bool:
    if not (
        actor.has_perm("courses.archive_course")
        and actor.has_perm("courses.restore_course")
    ):
        return False
    return (
        actor.has_perm("courses.view_all_courses")
        or course.project.manager_id == actor.pk
    )


def can_manage_course_trainers(actor: User, course: Course) -> bool:
    return actor.has_perm("courses.manage_course_trainers") and can_manage_course(
        actor, course
    )


def can_upload_course_file(actor: User, course: Course) -> bool:
    return actor.has_perm("courses.upload_course_file") and can_manage_course(
        actor, course
    )


def trainers_visible_to(actor: User, *, search: str = "") -> QuerySet[Trainer]:
    if not actor.has_perm("courses.view_trainer"):
        return Trainer.objects.none()
    queryset = Trainer.objects.all()
    if not actor.has_perm("courses.view_all_courses"):
        queryset = queryset.filter(is_archived=False)
    normalized = normalize_account_search(search)
    if normalized:
        queryset = queryset.filter(search_key__contains=normalized)
    return queryset.order_by("code")


def visible_trainer_or_404(actor: User, trainer_id: int) -> Trainer:
    try:
        return trainers_visible_to(actor).get(pk=trainer_id)
    except Trainer.DoesNotExist as error:
        raise Http404 from error


def course_history_visible_to(
    actor: User,
    course: Course,
) -> QuerySet[AuditEvent]:
    if not actor.has_perm("courses.view_course_history"):
        raise PermissionDenied("Course history permission is required.")
    if not (
        actor.has_perm("courses.view_all_courses")
        or course.project.manager_id == actor.pk
    ):
        raise PermissionDenied("Course history is not visible for this course.")
    return AuditEvent.objects.select_related("actor").filter(
        scope=AuditEvent.Scope.COURSES,
        target_type="course",
        target_id=str(course.pk),
    )
