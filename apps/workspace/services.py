"""Dashboard, search, saved-filter, and planning data shaping."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlencode

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.roles import role_label
from apps.accounts.services import managed_role_code
from apps.approvals.models import ApprovalRequest
from apps.approvals.selectors import (
    approval_requests_visible_to,
    milestones_visible_to,
)
from apps.attendance.selectors import pending_submissions_for, sessions_visible_to
from apps.courses.selectors import courses_visible_to
from apps.progress.services import project_progress_for
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to
from apps.workspace.models import SavedFilter

RESULT_LIMIT = 25
PLANNING_LIMIT = 200


@dataclass(frozen=True)
class DashboardCard:
    label: str
    value: int
    url: str


@dataclass(frozen=True)
class SearchSection:
    label: str
    items: tuple[Any, ...]
    total: int
    detail_url_name: str


@dataclass(frozen=True)
class PlanningItem:
    kind: str
    code: str
    label: str
    start: date
    end: date
    status: str
    url: str
    progress: str | None = None


def dashboard_context(actor: User, language_code: str) -> dict[str, Any]:
    """Build metrics strictly from already-scoped selectors."""
    projects = projects_visible_to(actor)
    courses = courses_visible_to(actor)
    tasks = tasks_visible_to(actor)
    approvals = approval_requests_visible_to(actor).filter(
        status__in=(
            ApprovalRequest.Status.PENDING_SUPERVISOR,
            ApprovalRequest.Status.PENDING_MANAGER,
        )
    )
    cards: list[DashboardCard] = []
    if actor.has_perm("projects.view_project"):
        cards.append(
            DashboardCard(
                str(_("Projects")), projects.count(), reverse("projects:list")
            )
        )
    if actor.has_perm("courses.view_course"):
        cards.append(
            DashboardCard(str(_("Courses")), courses.count(), reverse("courses:list"))
        )
    if actor.has_perm("tasks.view_task"):
        cards.append(
            DashboardCard(str(_("Tasks")), tasks.count(), reverse("tasks:list"))
        )
    if actor.has_perm("approvals.view_approvalrequest"):
        cards.append(
            DashboardCard(
                str(_("Pending approvals")),
                approvals.count(),
                reverse("approvals:queue"),
            )
        )
    if actor.has_perm("attendance.review_attendance"):
        cards.append(
            DashboardCard(
                str(_("Attendance reviews")),
                pending_submissions_for(actor).count(),
                reverse("attendance:review-queue"),
            )
        )

    progress_rows = []
    for project in projects[:5]:
        progress = project_progress_for(actor, project)
        if progress is not None:
            progress_rows.append(
                {
                    "project": project,
                    "label": project.localized_name(language_code),
                    "progress": progress,
                }
            )
    role_code = managed_role_code(actor)
    return {
        "dashboard_role": role_label(role_code),
        "cards": tuple(cards),
        "tasks": tuple(tasks[:8]),
        "progress_rows": tuple(progress_rows),
    }


def global_search(actor: User, query: str) -> tuple[SearchSection, ...]:
    """Search each domain independently without crossing its visibility selector."""
    sections = (
        (
            _("Projects"),
            projects_visible_to(actor, search=query),
            "projects:detail",
        ),
        (
            _("Courses"),
            courses_visible_to(actor, search=query),
            "courses:detail",
        ),
        (
            _("Tasks"),
            tasks_visible_to(actor, search=query),
            "tasks:detail",
        ),
        (
            _("Milestones"),
            milestones_visible_to(actor, search=query),
            "approvals:milestone_detail",
        ),
    )
    return tuple(
        SearchSection(
            label=str(label),
            items=tuple(queryset[:RESULT_LIMIT]),
            total=queryset.count(),
            detail_url_name=url_name,
        )
        for label, queryset, url_name in sections
    )


def _overlaps(
    start_field: str,
    end_field: str,
    start: date,
    end: date,
) -> dict[str, Any]:
    return {f"{start_field}__lte": end, f"{end_field}__gte": start}


def planning_items(
    actor: User,
    *,
    language_code: str,
    start: date,
    end: date,
    query: str = "",
    include_sessions: bool = False,
    include_progress: bool = False,
) -> tuple[PlanningItem, ...]:
    """Shape a bounded, permission-safe read-only planning data set."""
    items: list[PlanningItem] = []
    projects = tuple(
        projects_visible_to(actor, search=query).filter(
            **_overlaps("start_date", "end_date", start, end)
        )[:PLANNING_LIMIT]
    )
    courses = tuple(
        courses_visible_to(actor, search=query).filter(
            start_at__date__lte=end,
            end_at__date__gte=start,
        )[:PLANNING_LIMIT]
    )
    tasks = tuple(
        tasks_visible_to(actor, search=query).filter(
            start_date__isnull=False,
            due_date__isnull=False,
            start_date__lte=end,
            due_date__gte=start,
        )[:PLANNING_LIMIT]
    )
    milestones = tuple(
        milestones_visible_to(actor, search=query).filter(
            start_date__lte=end,
            due_date__gte=start,
        )[:PLANNING_LIMIT]
    )

    for project in projects:
        progress_label = None
        if include_progress:
            result = project_progress_for(actor, project)
            progress_label = str(result.percentage) if result is not None else None
        items.append(
            PlanningItem(
                kind=str(_("Project")),
                code=project.code,
                label=project.localized_name(language_code),
                start=project.start_date,
                end=project.end_date,
                status=project.get_status_display(),
                url=reverse("projects:detail", args=(project.pk,)),
                progress=progress_label,
            )
        )
    for course in courses:
        items.append(
            PlanningItem(
                kind=str(_("Course")),
                code=course.code,
                label=course.localized_name(language_code),
                start=course.start_at.date(),
                end=course.end_at.date(),
                status=course.get_status_display(),
                url=reverse("courses:detail", args=(course.pk,)),
            )
        )
    for task in tasks:
        assert task.start_date is not None and task.due_date is not None
        items.append(
            PlanningItem(
                kind=str(_("Task")),
                code=task.code,
                label=task.localized_name(language_code),
                start=task.start_date,
                end=task.due_date,
                status=task.get_status_display(),
                url=reverse("tasks:detail", args=(task.pk,)),
            )
        )
    for milestone in milestones:
        items.append(
            PlanningItem(
                kind=str(_("Milestone")),
                code=milestone.code,
                label=milestone.localized_name(language_code),
                start=milestone.start_date,
                end=milestone.due_date,
                status=milestone.get_status_display(),
                url=reverse("approvals:milestone_detail", args=(milestone.pk,)),
            )
        )
    if include_sessions:
        for session in sessions_visible_to(actor).filter(
            start_at__date__lte=end,
            end_at__date__gte=start,
        )[:PLANNING_LIMIT]:
            items.append(
                PlanningItem(
                    kind=str(_("Session")),
                    code=f"S-{session.pk}",
                    label=(
                        session.title_ar if language_code == "ar" else session.title_en
                    ),
                    start=session.start_at.date(),
                    end=session.end_at.date(),
                    status=str(_("Scheduled")),
                    url=reverse("attendance:detail", args=(session.pk,)),
                )
            )
    items.sort(key=lambda item: (item.start, item.end, item.kind, item.code))
    return tuple(items[:PLANNING_LIMIT])


def kanban_columns(actor: User, query: str) -> tuple[dict[str, Any], ...]:
    tasks = tuple(tasks_visible_to(actor, search=query)[:PLANNING_LIMIT])
    return tuple(
        {
            "code": status,
            "label": str(label),
            "tasks": tuple(task for task in tasks if task.status == status),
        }
        for status, label in Task.Status.choices
    )


@transaction.atomic
def save_filter(
    *,
    owner: User,
    name: str,
    view_type: str,
    criteria: dict[str, str],
) -> SavedFilter:
    try:
        return SavedFilter.objects.create(
            owner=owner,
            name=name,
            view_type=view_type,
            criteria=criteria,
            schema_version=1,
        )
    except IntegrityError as error:
        raise ValueError(_("A saved filter with this name already exists.")) from error


def saved_filter_url(saved_filter: SavedFilter) -> str:
    route_names: dict[str, str] = {
        SavedFilter.ViewType.SEARCH: "workspace:search",
        SavedFilter.ViewType.KANBAN: "workspace:kanban",
        SavedFilter.ViewType.CALENDAR: "workspace:calendar",
        SavedFilter.ViewType.TIMELINE: "workspace:timeline",
        SavedFilter.ViewType.GANTT: "workspace:gantt",
    }
    route = reverse(route_names[saved_filter.view_type])
    return f"{route}?{urlencode(saved_filter.criteria)}"
