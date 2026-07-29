"""Permission-scoped Phase 8 reads."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.courses.models import Course
from apps.trainees.models import CourseEnrollment, ImportBatch


def enrollments_visible_to(
    actor: User,
    *,
    course: Course | None = None,
    search: str = "",
    include_archived: bool = False,
) -> QuerySet[CourseEnrollment]:
    queryset = CourseEnrollment.objects.select_related(
        "course", "course__project", "trainee"
    )
    if actor.has_perm("trainees.view_all_enrollments"):
        visible = queryset
    elif actor.has_perm("trainees.view_managed_enrollments"):
        visible = queryset.filter(course__project__manager=actor)
    elif actor.has_perm("trainees.view_roster_enrollments"):
        visible = queryset.filter(
            Q(course__project__supervisor=actor)
            | Q(
                course__project__memberships__user=actor,
                course__project__memberships__removed_at__isnull=True,
            ),
            course__project__status="active",
            course__project__is_archived=False,
            course__status=Course.Status.ACTIVE,
            course__is_archived=False,
        )
    else:
        visible = queryset.none()
    if course is not None:
        visible = visible.filter(course=course)
    if not include_archived or actor.has_perm("trainees.view_roster_enrollments"):
        visible = visible.filter(is_archived=False)
    search = search.strip()
    if search:
        visible = visible.filter(
            Q(trainee__full_name__icontains=search)
            | Q(trainee__phone__icontains=search)
            | Q(trainee_number__icontains=search)
        )
    return visible.distinct().order_by("course__code", "trainee_number")


def visible_enrollment_or_404(actor: User, enrollment_id: int) -> CourseEnrollment:
    try:
        return enrollments_visible_to(actor, include_archived=True).get(
            pk=enrollment_id
        )
    except CourseEnrollment.DoesNotExist as error:
        raise Http404 from error


def can_manage_enrollment(actor: User, course: Course) -> bool:
    return (
        actor.has_perm("trainees.add_courseenrollment")
        and not course.is_archived
        and not course.project.is_archived
        and course.status != Course.Status.COMPLETED
        and (
            actor.has_perm("trainees.view_all_enrollments")
            or course.project.manager_id == actor.pk
        )
    )


def can_archive_enrollment(actor: User, enrollment: CourseEnrollment) -> bool:
    return (
        actor.has_perm("trainees.archive_enrollment")
        and actor.has_perm("trainees.restore_enrollment")
        and not enrollment.course.is_archived
        and not enrollment.course.project.is_archived
        and enrollment.course.status != Course.Status.COMPLETED
        and (
            actor.has_perm("trainees.view_all_enrollments")
            or enrollment.course.project.manager_id == actor.pk
        )
    )


def import_batches_visible_to(actor: User) -> QuerySet[ImportBatch]:
    if not actor.has_perm("trainees.view_import_history"):
        return ImportBatch.objects.none()
    queryset = ImportBatch.objects.select_related(
        "course", "course__project", "uploaded_by", "confirmed_by"
    )
    if actor.has_perm("trainees.view_all_enrollments"):
        return queryset
    return queryset.filter(course__project__manager=actor)


def visible_batch_or_404(actor: User, batch_id: int) -> ImportBatch:
    try:
        return import_batches_visible_to(actor).get(pk=batch_id)
    except ImportBatch.DoesNotExist as error:
        raise Http404 from error


def ensure_import_scope(actor: User, course: Course, *, confirm: bool = False) -> None:
    permission = (
        "trainees.confirm_trainee_import" if confirm else "trainees.import_trainees"
    )
    if not actor.has_perm(permission) or not can_manage_enrollment(actor, course):
        raise PermissionDenied
