"""Authorization-aware Phase 6 progress orchestration."""

from collections import defaultdict
from collections.abc import Iterable

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.approvals.models import Milestone
from apps.approvals.selectors import milestones_visible_to
from apps.courses.models import Course
from apps.courses.selectors import courses_visible_to
from apps.progress.calculations import (
    HUNDRED,
    ZERO,
    ProgressResult,
    ProgressState,
    TaskProgressInput,
    TaskProgressTree,
    average,
)
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to


def _task_inputs(tasks: Iterable[Task]) -> tuple[TaskProgressInput, ...]:
    return tuple(
        TaskProgressInput(
            task_id=task.pk,
            parent_id=task.parent_id,
            status=task.status,
            is_archived=task.is_archived,
        )
        for task in tasks
    )


def _owner_tasks(task: Task) -> QuerySet[Task]:
    if task.project_id:
        return Task.objects.filter(project_id=task.project_id)
    course_id = task.course_id
    assert course_id is not None
    return Task.objects.filter(course_id=course_id)


def _can_view_complete_task_context(actor: User, task: Task) -> bool:
    if actor.has_perm("tasks.view_all_tasks"):
        return True
    if actor.has_perm("tasks.view_managed_tasks"):
        if task.project_id:
            project = task.project
            assert project is not None
            manager_id = project.manager_id
        else:
            course = task.course
            assert course is not None
            manager_id = course.project.manager_id
        return manager_id == actor.pk
    return actor.has_perm("tasks.view_context_tasks")


def task_progress_for(actor: User, task: Task) -> ProgressResult | None:
    """Return task progress only when the complete hierarchy is visible."""
    if not tasks_visible_to(actor, include_archived=True).filter(pk=task.pk).exists():
        return None
    if not _can_view_complete_task_context(actor, task):
        return None
    return calculate_task_progress(task)


def calculate_task_progress(task: Task) -> ProgressResult:
    """Calculate one task for trusted domain workflows."""
    tree = TaskProgressTree(_task_inputs(_owner_tasks(task)))
    return tree.result_for(task.pk)


def _can_view_course_progress(actor: User, course: Course) -> bool:
    if actor.has_perm("tasks.view_all_tasks"):
        return True
    if actor.has_perm("tasks.view_managed_tasks"):
        return course.project.manager_id == actor.pk
    return (
        actor.has_perm("tasks.view_context_tasks")
        and course.status == Course.Status.ACTIVE
        and not course.is_archived
        and course.project.status == Project.Status.ACTIVE
        and not course.project.is_archived
    )


def _course_progress_from_tasks(
    course: Course,
    tasks: Iterable[Task],
) -> ProgressResult:
    if course.is_archived or course.status == Course.Status.CANCELLED:
        return ProgressResult.excluded()
    return TaskProgressTree(_task_inputs(tasks)).root_result()


def course_progress_for(actor: User, course: Course) -> ProgressResult | None:
    """Return course progress without exceeding the actor's source scope."""
    if (
        not courses_visible_to(actor, include_archived=True)
        .filter(pk=course.pk)
        .exists()
    ):
        return None
    if not _can_view_course_progress(actor, course):
        return None
    return calculate_course_progress(course)


def calculate_course_progress(course: Course) -> ProgressResult:
    """Calculate one course for trusted domain workflows."""
    return _course_progress_from_tasks(course, Task.objects.filter(course=course))


def calculate_milestone_progress(milestone: Milestone) -> ProgressResult:
    """Return approved status-based milestone progress."""
    if milestone.is_archived or milestone.status == Milestone.Status.CANCELLED:
        return ProgressResult.excluded()
    return ProgressResult(
        raw_percentage=(
            HUNDRED if milestone.status == Milestone.Status.COMPLETED else ZERO
        ),
        state=ProgressState.VALUE,
        included_items=1,
    )


def milestone_progress_for(
    actor: User,
    milestone: Milestone,
) -> ProgressResult | None:
    """Return milestone progress only inside the actor's object scope."""
    if (
        not milestones_visible_to(actor, include_archived=True)
        .filter(pk=milestone.pk)
        .exists()
    ):
        return None
    return calculate_milestone_progress(milestone)


def _can_view_project_progress(actor: User, project: Project) -> bool:
    if actor.has_perm("tasks.view_all_tasks"):
        return True
    if actor.has_perm("tasks.view_managed_tasks"):
        return project.manager_id == actor.pk
    if not (
        actor.has_perm("tasks.view_context_tasks")
        and project.status == Project.Status.ACTIVE
        and not project.is_archived
    ):
        return False
    return (
        not Course.objects.filter(project=project, is_archived=False)
        .exclude(status__in=(Course.Status.ACTIVE, Course.Status.CANCELLED))
        .exists()
    )


def project_progress_for(actor: User, project: Project) -> ProgressResult | None:
    """Return equal-weight available task/course category progress."""
    if (
        not projects_visible_to(actor, include_archived=True)
        .filter(pk=project.pk)
        .exists()
    ):
        return None
    if not _can_view_project_progress(actor, project):
        return None
    return calculate_project_progress(project)


def calculate_project_progress(project: Project) -> ProgressResult:
    """Calculate project categories for trusted domain workflows."""
    if project.is_archived or project.status == Project.Status.CANCELLED:
        return ProgressResult.excluded()

    direct_tasks = tuple(Task.objects.filter(project=project))
    task_category = TaskProgressTree(_task_inputs(direct_tasks)).root_result()

    courses = tuple(Course.objects.filter(project=project).order_by("pk"))
    course_tasks: dict[int, list[Task]] = defaultdict(list)
    for task in Task.objects.filter(course__project=project).order_by("pk"):
        if task.course_id is not None:
            course_tasks[task.course_id].append(task)
    course_results = [
        _course_progress_from_tasks(course, course_tasks[course.pk])
        for course in courses
    ]
    course_values = [
        result.raw_percentage
        for result in course_results
        if result.state != ProgressState.EXCLUDED
    ]

    category_values = []
    if task_category.state == ProgressState.VALUE:
        category_values.append(task_category.raw_percentage)
    if course_values:
        category_values.append(average(course_values))
    milestone_values = [
        result.raw_percentage
        for milestone in Milestone.objects.filter(project=project).order_by("pk")
        if (result := calculate_milestone_progress(milestone)).state
        != ProgressState.EXCLUDED
    ]
    if milestone_values:
        category_values.append(average(milestone_values))
    if not category_values:
        return ProgressResult.empty()
    return ProgressResult(
        raw_percentage=average(category_values),
        state=ProgressState.VALUE,
        included_items=len(category_values),
    )
