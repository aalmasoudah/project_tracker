"""The complete allowlist of bounded, permission-rechecked read tools."""

import json
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal
from typing import Final

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest, Milestone
from apps.approvals.selectors import (
    approval_requests_visible_to,
    milestones_visible_to,
)
from apps.progress.services import project_progress_for
from apps.project_agents.models import AgentMemory, AgentRun
from apps.project_agents.policies import can_view_agent_run
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Task, TaskAssignment
from apps.tasks.selectors import tasks_visible_to

ToolResult = dict[str, object]
ToolFunction = Callable[[AgentRun, User], ToolResult]


def _require_scope(run: AgentRun, actor: User) -> Project:
    if not can_view_agent_run(actor, run):
        raise PermissionDenied("Project-agent scope is no longer available.")
    try:
        return projects_visible_to(actor, include_archived=True).get(pk=run.project_id)
    except Project.DoesNotExist as error:
        raise PermissionDenied("Project-agent scope is no longer available.") from error


def _task_queryset(run: AgentRun, actor: User) -> QuerySet[Task]:
    return tasks_visible_to(actor).filter(
        Q(project_id=run.project_id) | Q(course__project_id=run.project_id)
    )


def _source(
    *,
    ref: str,
    source_type: str,
    source_id: object,
    label: str,
    path: str,
    data: dict[str, object],
) -> dict[str, object]:
    return {
        "ref": ref,
        "type": source_type,
        "id": str(source_id),
        "label": label[:250],
        "path": path,
        "data": data,
    }


def get_project_snapshot(run: AgentRun, actor: User) -> ToolResult:
    project = _require_scope(run, actor)
    tasks = _task_queryset(run, actor)
    active = tasks.exclude(status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
    overdue = active.filter(due_date__lt=timezone.localdate()).count()
    blocked = active.filter(status=Task.Status.BLOCKED).count()
    source = _source(
        ref=f"project:{project.pk}",
        source_type="project",
        source_id=project.pk,
        label=f"{project.code} - {project.localized_name(run.language)}",
        path=reverse("projects:detail", args=(project.pk,)),
        data={
            "code": project.code,
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date.isoformat(),
            "end_date": project.end_date.isoformat(),
            "active_tasks": active.count(),
            "overdue_tasks": overdue,
            "blocked_tasks": blocked,
        },
    )
    return {"tool": "get_project_snapshot", "items": [source], "truncated": False}


def list_overdue_and_blocked_tasks(run: AgentRun, actor: User) -> ToolResult:
    _require_scope(run, actor)
    today = timezone.localdate()
    queryset = (
        _task_queryset(run, actor)
        .filter(Q(due_date__lt=today) | Q(status=Task.Status.BLOCKED))
        .exclude(status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
        .order_by("due_date", "code")
    )
    limit = int(settings.PROJECT_AGENT_MAX_TOOL_RECORDS)
    rows = list(queryset[: limit + 1])
    items = [
        _source(
            ref=f"task:{task.pk}",
            source_type="task",
            source_id=task.pk,
            label=f"{task.code} - {task.localized_name(run.language)}",
            path=reverse("tasks:detail", args=(task.pk,)),
            data={
                "task_id": task.pk,
                "code": task.code,
                "name": task.localized_name(run.language),
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "actual_hours": str(task.actual_hours)
                if task.actual_hours is not None
                else None,
                "blocking_reason": task.blocking_reason[:500],
                "updated_at": task.updated_at.isoformat(),
            },
        )
        for task in rows[:limit]
    ]
    return {
        "tool": "list_overdue_and_blocked_tasks",
        "items": items,
        "truncated": len(rows) > limit,
    }


def get_upcoming_milestones(run: AgentRun, actor: User) -> ToolResult:
    _require_scope(run, actor)
    today = timezone.localdate()
    queryset = (
        milestones_visible_to(actor)
        .filter(project_id=run.project_id, due_date__gte=today)
        .exclude(status__in=(Milestone.Status.COMPLETED, Milestone.Status.CANCELLED))
        .order_by("due_date", "code")
    )
    limit = int(settings.PROJECT_AGENT_MAX_TOOL_RECORDS)
    rows = list(queryset[: limit + 1])
    items = [
        _source(
            ref=f"milestone:{item.pk}",
            source_type="milestone",
            source_id=item.pk,
            label=f"{item.code} - {item.localized_name(run.language)}",
            path=reverse("approvals:milestone_detail", args=(item.pk,)),
            data={
                "code": item.code,
                "name": item.localized_name(run.language),
                "status": item.status,
                "start_date": item.start_date.isoformat(),
                "due_date": item.due_date.isoformat(),
            },
        )
        for item in rows[:limit]
    ]
    return {
        "tool": "get_upcoming_milestones",
        "items": items,
        "truncated": len(rows) > limit,
    }


def get_pending_approvals(run: AgentRun, actor: User) -> ToolResult:
    _require_scope(run, actor)
    pending = (
        ApprovalRequest.Status.PENDING_SUPERVISOR,
        ApprovalRequest.Status.PENDING_MANAGER,
    )
    queryset = (
        approval_requests_visible_to(actor)
        .filter(status__in=pending)
        .filter(
            Q(task__project_id=run.project_id)
            | Q(task__course__project_id=run.project_id)
            | Q(course__project_id=run.project_id)
            | Q(milestone__project_id=run.project_id)
            | Q(project_id=run.project_id)
        )
    )
    limit = int(settings.PROJECT_AGENT_MAX_TOOL_RECORDS)
    rows = list(queryset[: limit + 1])
    items = [
        _source(
            ref=f"approval:{item.pk}",
            source_type="approval",
            source_id=item.pk,
            label=f"{item.target_type} - {item.target_code}",
            path=reverse("approvals:detail", args=(item.pk,)),
            data={
                "target_type": item.target_type,
                "target_code": item.target_code,
                "status": item.status,
                "submitted_at": item.submitted_at.isoformat(),
            },
        )
        for item in rows[:limit]
    ]
    return {
        "tool": "get_pending_approvals",
        "items": items,
        "truncated": len(rows) > limit,
    }


def get_team_workload(run: AgentRun, actor: User) -> ToolResult:
    project = _require_scope(run, actor)
    users: dict[int, User] = {project.manager_id: project.manager}
    if project.supervisor_id and project.supervisor:
        users[project.supervisor_id] = project.supervisor
    for membership in project.memberships.select_related("user").filter(
        removed_at__isnull=True, user__is_active=True
    ):
        users[membership.user_id] = membership.user
    limit = int(settings.PROJECT_AGENT_MAX_TOOL_RECORDS)
    prioritized_ids = [project.manager_id]
    if project.supervisor_id:
        prioritized_ids.append(project.supervisor_id)
    prioritized_ids.extend(
        sorted(user_id for user_id in users if user_id not in prioritized_ids)
    )
    selected_ids = prioritized_ids[:limit]
    workloads: dict[int, dict[str, Decimal | int]] = defaultdict(
        lambda: {
            "active_tasks": 0,
            "estimated_hours": Decimal("0"),
            "actual_hours": Decimal("0"),
        }
    )
    visible_ids = _task_queryset(run, actor).values_list("pk", flat=True)
    assignments = (
        TaskAssignment.objects.select_related("task")
        .filter(
            task_id__in=visible_ids,
            user_id__in=selected_ids,
            removed_at__isnull=True,
        )
        .exclude(task__status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
    )
    for assignment in assignments:
        item = workloads[assignment.user_id]
        item["active_tasks"] = int(item["active_tasks"]) + 1
        item["estimated_hours"] = Decimal(item["estimated_hours"]) + (
            assignment.task.estimated_hours or 0
        )
        item["actual_hours"] = Decimal(item["actual_hours"]) + (
            assignment.task.actual_hours or 0
        )
    items = []
    for user_id in selected_ids:
        user = users[user_id]
        workload = workloads[user_id]
        label = user.get_full_name().strip() or user.username
        items.append(
            _source(
                ref=f"team:{user_id}",
                source_type="team_member",
                source_id=user_id,
                label=label,
                path=reverse("projects:detail", args=(project.pk,)),
                data={
                    "user_id": user_id,
                    "display_name": label,
                    "active_tasks": workload["active_tasks"],
                    "estimated_hours": str(workload["estimated_hours"]),
                    "actual_hours": str(workload["actual_hours"]),
                },
            )
        )
    return {
        "tool": "get_team_workload",
        "items": items,
        "truncated": len(users) > limit,
    }


def calculate_project_progress(run: AgentRun, actor: User) -> ToolResult:
    project = _require_scope(run, actor)
    result = project_progress_for(actor, project)
    data: dict[str, object] = {
        "state": result.state.value if result is not None else "unavailable",
        "percentage": str(result.percentage) if result is not None else None,
        "included_items": result.included_items if result is not None else 0,
        "excluded_items": result.excluded_items if result is not None else 0,
    }
    item = _source(
        ref=f"progress:{project.pk}",
        source_type="progress",
        source_id=project.pk,
        label=f"{project.code} progress",
        path=reverse("projects:detail", args=(project.pk,)),
        data=data,
    )
    return {"tool": "calculate_project_progress", "items": [item], "truncated": False}


def recall_reviewed_agent_runs(run: AgentRun, actor: User) -> ToolResult:
    _require_scope(run, actor)
    limit = min(int(settings.PROJECT_AGENT_MAX_MEMORIES), 5)
    memories = (
        AgentMemory.objects.select_related("source_run")
        .filter(
            project_id=run.project_id,
            source_run__status=AgentRun.Status.COMPLETED,
            source_run__reviewed_at__isnull=False,
        )
        .exclude(source_run_id=run.pk)[:limit]
    )
    items = [
        _source(
            ref=f"memory:{memory.pk}",
            source_type="reviewed_memory",
            source_id=memory.pk,
            label=f"Reviewed run {memory.source_run_id}",
            path=reverse("project_agents:detail", args=(memory.source_run_id,)),
            data={
                "reviewed_at": memory.reviewed_at.isoformat(),
                "summary": memory.reviewed_summary,
                "source_citations": memory.citations,
            },
        )
        for memory in memories
    ]
    return {"tool": "recall_reviewed_agent_runs", "items": items, "truncated": False}


TOOL_REGISTRY: Final[dict[str, ToolFunction]] = {
    "get_project_snapshot": get_project_snapshot,
    "list_overdue_and_blocked_tasks": list_overdue_and_blocked_tasks,
    "get_upcoming_milestones": get_upcoming_milestones,
    "get_pending_approvals": get_pending_approvals,
    "get_team_workload": get_team_workload,
    "calculate_project_progress": calculate_project_progress,
    "recall_reviewed_agent_runs": recall_reviewed_agent_runs,
}


def execute_read_tool(*, run: AgentRun, actor: User, tool_code: str) -> ToolResult:
    try:
        function = TOOL_REGISTRY[tool_code]
    except KeyError as error:
        raise ValidationError(
            "The requested project-agent tool is not allowed."
        ) from error
    result = function(run, actor)
    encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(encoded) > int(settings.PROJECT_AGENT_MAX_TOOL_RESULT_BYTES):
        raise ValidationError("The project-agent tool result is too large.")
    return result


def observed_references(
    run: AgentRun,
) -> tuple[frozenset[str], frozenset[int], frozenset[int]]:
    citations: set[str] = set()
    task_ids: set[int] = set()
    user_ids: set[int] = set()
    for call in run.tool_calls.filter(status="completed").only("safe_result"):
        result = call.safe_result
        if not isinstance(result, dict):
            continue
        items = result.get("items", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            ref = item.get("ref")
            if isinstance(ref, str):
                citations.add(ref)
            data = item.get("data")
            if not isinstance(data, dict):
                continue
            task_id = data.get("task_id")
            user_id = data.get("user_id")
            if isinstance(task_id, int):
                task_ids.add(task_id)
            if isinstance(user_id, int):
                user_ids.add(user_id)
    return frozenset(citations), frozenset(task_ids), frozenset(user_ids)
