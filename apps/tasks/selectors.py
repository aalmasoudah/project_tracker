"""Permission-scoped task query helpers."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.audit.models import AuditEvent
from apps.tasks.models import Task


def tasks_visible_to(
    actor: User,
    *,
    search: str = "",
    status: str = "",
    include_archived: bool = False,
) -> QuerySet[Task]:
    queryset = Task.objects.select_related(
        "project",
        "project__manager",
        "course",
        "course__project",
        "course__project__manager",
        "parent",
    )
    if actor.has_perm("tasks.view_all_tasks"):
        visible = queryset
    elif actor.has_perm("tasks.view_managed_tasks"):
        visible = queryset.filter(
            Q(project__manager=actor) | Q(course__project__manager=actor)
        )
    elif actor.has_perm("tasks.view_context_tasks"):
        visible = queryset.filter(
            Q(project__supervisor=actor)
            | Q(
                project__memberships__user=actor,
                project__memberships__removed_at__isnull=True,
            )
            | Q(course__project__supervisor=actor)
            | Q(
                course__project__memberships__user=actor,
                course__project__memberships__removed_at__isnull=True,
            ),
            is_archived=False,
        ).filter(
            Q(project__status="active", project__is_archived=False)
            | Q(
                course__status="active",
                course__is_archived=False,
                course__project__status="active",
                course__project__is_archived=False,
            )
        )
    elif actor.has_perm("tasks.view_assigned_tasks"):
        visible = queryset.filter(
            assignments__user=actor,
            assignments__removed_at__isnull=True,
            is_archived=False,
        ).filter(
            Q(project__status="active", project__is_archived=False)
            | Q(
                course__status="active",
                course__is_archived=False,
                course__project__status="active",
                course__project__is_archived=False,
            )
        )
    else:
        visible = queryset.none()
    if not include_archived or not (
        actor.has_perm("tasks.view_all_tasks")
        or actor.has_perm("tasks.view_managed_tasks")
    ):
        visible = visible.filter(is_archived=False)
    normalized = normalize_account_search(search)
    if normalized:
        visible = visible.filter(search_key__contains=normalized)
    if status in Task.Status.values:
        visible = visible.filter(status=status)
    return visible.distinct().order_by("code")


def visible_task_or_404(actor: User, task_id: int) -> Task:
    try:
        return tasks_visible_to(actor, include_archived=True).get(pk=task_id)
    except Task.DoesNotExist as error:
        raise Http404 from error


def task_manager_id(task: Task) -> int:
    if task.project_id:
        project = task.project
        assert project is not None
        return project.manager_id
    course = task.course
    assert course is not None
    return course.project.manager_id


def can_manage_task(actor: User, task: Task) -> bool:
    if not actor.has_perm("tasks.change_task") or task.is_archived:
        return False
    return actor.has_perm("tasks.view_all_tasks") or task_manager_id(task) == actor.pk


def is_active_assignee(actor: User, task: Task) -> bool:
    return task.assignments.filter(user=actor, removed_at__isnull=True).exists()


def can_update_assigned_task(actor: User, task: Task) -> bool:
    return (
        actor.has_perm("tasks.update_assigned_task")
        and not task.is_archived
        and is_active_assignee(actor, task)
    )


def can_archive_task(actor: User, task: Task) -> bool:
    return actor.has_perm("tasks.archive_task") and (
        actor.has_perm("tasks.view_all_tasks") or task_manager_id(task) == actor.pk
    )


def can_restore_task(actor: User, task: Task) -> bool:
    return actor.has_perm("tasks.restore_task") and (
        actor.has_perm("tasks.view_all_tasks") or task_manager_id(task) == actor.pk
    )


def task_history_visible_to(
    actor: User,
    task: Task,
) -> QuerySet[AuditEvent]:
    if not actor.has_perm("tasks.view_task_history"):
        raise PermissionDenied("Task history permission is required.")
    if not (
        actor.has_perm("tasks.view_all_tasks") or task_manager_id(task) == actor.pk
    ):
        raise PermissionDenied("Task history is not visible.")
    return AuditEvent.objects.select_related("actor").filter(
        scope=AuditEvent.Scope.TASKS,
        target_type="task",
        target_id=str(task.pk),
    )
