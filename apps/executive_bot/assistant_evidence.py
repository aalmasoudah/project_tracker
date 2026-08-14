"""Small permission-scoped evidence set for the Telegram AI assistant."""

from dataclasses import dataclass
from datetime import date
from typing import cast

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest
from apps.approvals.selectors import approval_requests_visible_to
from apps.executive_bot.evidence import _active_task_queryset
from apps.progress.services import project_progress_for
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Task

PROJECT_PROGRESS_FOCUS = "project_progress"


def _question_focus(question: str) -> str:
    folded = question.casefold()
    project_terms = ("project", "projects", "مشروع", "مشاريع")
    progress_terms = (
        "progress",
        "completion",
        "complete",
        "completed",
        "percentage",
        "percent",
        "%",
        "تقدم",
        "إنجاز",
        "اكتمال",
        "نسبة",
        "نسب",
    )
    if any(term in folded for term in project_terms) and any(
        term in folded for term in progress_terms
    ):
        return PROJECT_PROGRESS_FOCUS
    return "general"


@dataclass(frozen=True, slots=True)
class AssistantEvidence:
    provider_payload: dict[str, object]
    allowed_citations: frozenset[str]
    source_labels: dict[str, str]
    source_count: int
    truncated: bool


def _task_project(task: Task) -> Project:
    if task.project_id:
        assert task.project is not None
        return task.project
    assert task.course is not None
    return task.course.project


def _risk_score(task: Task, *, today: date) -> int:
    priority_scores: dict[str, int] = {
        Task.Priority.LOW: 0,
        Task.Priority.MEDIUM: 10,
        Task.Priority.HIGH: 25,
        Task.Priority.CRITICAL: 40,
    }
    score = priority_scores[task.priority]
    if task.status == Task.Status.BLOCKED:
        score += 35
    if task.due_date is not None:
        days_to_due = (task.due_date - today).days
        if days_to_due < 0:
            score += 40 + min(abs(days_to_due), 20)
        elif days_to_due <= 3:
            score += 22
        elif days_to_due <= 7:
            score += 12
    project = _task_project(task)
    if project.status == Project.Status.ON_HOLD:
        score += 20
    if project.priority == Project.Priority.CRITICAL:
        score += 10
    return score


def _target_details(approval: ApprovalRequest, language: str) -> tuple[str, str, str]:
    if approval.task_id and approval.task is not None:
        task = approval.task
        project = _task_project(task)
        return task.code, task.localized_name(language), project.code
    if approval.course_id and approval.course is not None:
        return (
            approval.course.code,
            approval.course.localized_name(language),
            approval.course.project.code,
        )
    if approval.milestone_id and approval.milestone is not None:
        return (
            approval.milestone.code,
            approval.milestone.localized_name(language),
            approval.milestone.project.code,
        )
    assert approval.project is not None
    return (
        approval.project.code,
        approval.project.localized_name(language),
        approval.project.code,
    )


def build_assistant_evidence(
    *, actor: User, question: str, language: str
) -> AssistantEvidence:
    today = timezone.localdate()
    limit = int(settings.EXECUTIVE_ASSISTANT_EVIDENCE_LIMIT)
    question_focus = _question_focus(question)
    source_labels: dict[str, str] = {}
    task_items: list[dict[str, object]] = []
    project_items: list[dict[str, object]] = []
    approval_items: list[dict[str, object]] = []

    task_candidates_truncated = False
    ranked_tasks: list[Task] = []
    task_limit = (
        0 if question_focus == PROJECT_PROGRESS_FOCUS else max(1, (limit * 3) // 4)
    )
    if task_limit:
        task_queryset = _active_task_queryset(actor).annotate(
            active_assignee_count=Count(
                "assignments",
                filter=Q(assignments__removed_at__isnull=True),
                distinct=True,
            )
        )
        candidate_tasks = list(task_queryset[:501])
        task_candidates_truncated = len(candidate_tasks) > 500
        ranked_tasks = sorted(
            candidate_tasks[:500],
            key=lambda task: (
                -_risk_score(task, today=today),
                task.due_date or date.max,
                task.code,
            ),
        )
    for task in ranked_tasks[:task_limit]:
        project = _task_project(task)
        source_ref = f"task:{task.pk}"
        source_labels[source_ref] = (
            f"{task.code} - {task.localized_name(language)} ({project.code})"
        )
        task_items.append(
            {
                "source_ref": source_ref,
                "code": task.code,
                "name": task.localized_name(language),
                "project_code": project.code,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "days_to_due": (
                    (task.due_date - today).days if task.due_date else None
                ),
                "has_blocker": task.status == Task.Status.BLOCKED,
                "active_assignee_count": cast(
                    int, task.__dict__["active_assignee_count"]
                ),
                "local_risk_score": _risk_score(task, today=today),
            }
        )

    remaining = limit - len(source_labels)
    visible_projects = list(
        projects_visible_to(actor)
        .exclude(status__in=(Project.Status.CANCELLED, Project.Status.COMPLETED))
        .order_by("code")[:101]
    )
    project_candidates_truncated = len(visible_projects) > 100
    referenced_project_codes = {item["project_code"] for item in task_items}
    visible_projects.sort(
        key=lambda project: (
            project.code not in referenced_project_codes,
            project.status != Project.Status.ON_HOLD,
            project.priority != Project.Priority.CRITICAL,
            project.end_date,
            project.code,
        )
    )
    preferred_project_budget = (
        limit if question_focus == PROJECT_PROGRESS_FOCUS else max(1, limit // 6)
    )
    project_budget = min(remaining, preferred_project_budget) if remaining else 0
    for project in visible_projects[:project_budget]:
        progress = project_progress_for(actor, project)
        source_ref = f"project:{project.pk}"
        source_labels[source_ref] = (
            f"{project.code} - {project.localized_name(language)}"
        )
        project_items.append(
            {
                "source_ref": source_ref,
                "code": project.code,
                "name": project.localized_name(language),
                "status": project.status,
                "priority": project.priority,
                "end_date": project.end_date.isoformat(),
                "days_to_end": (project.end_date - today).days,
                "progress_percent": (
                    str(progress.percentage) if progress is not None else None
                ),
            }
        )

    remaining = (
        0 if question_focus == PROJECT_PROGRESS_FOCUS else limit - len(source_labels)
    )
    pending_statuses = (
        ApprovalRequest.Status.PENDING_SUPERVISOR,
        ApprovalRequest.Status.PENDING_MANAGER,
    )
    approval_candidates: list[ApprovalRequest] = []
    approval_candidates_truncated = False
    if remaining:
        approval_candidates = list(
            approval_requests_visible_to(actor)
            .filter(status__in=pending_statuses)
            .order_by("submitted_at", "pk")[:101]
        )
        approval_candidates_truncated = len(approval_candidates) > 100
    for approval in approval_candidates[:remaining]:
        target_code, target_name, project_code = _target_details(approval, language)
        source_ref = f"approval:{approval.pk}"
        source_labels[source_ref] = f"{target_code} - {target_name} ({project_code})"
        approval_items.append(
            {
                "source_ref": source_ref,
                "target_type": approval.target_type,
                "target_code": target_code,
                "project_code": project_code,
                "status": approval.status,
                "waiting_days": (timezone.now() - approval.submitted_at).days,
            }
        )

    if question_focus == PROJECT_PROGRESS_FOCUS:
        truncated = project_candidates_truncated or len(visible_projects) > len(
            project_items
        )
    else:
        truncated = (
            task_candidates_truncated
            or project_candidates_truncated
            or approval_candidates_truncated
            or len(ranked_tasks) > len(task_items)
            or len(visible_projects) > len(project_items)
            or len(approval_candidates) > len(approval_items)
        )
    payload: dict[str, object] = {
        "question": question,
        "question_language": language,
        "question_focus": question_focus,
        "as_of_date": today.isoformat(),
        "evidence_rules": {
            "read_only": True,
            "locally_ranked": True,
            "truncated": truncated,
        },
        "tasks": task_items,
        "projects": project_items,
        "pending_approvals": approval_items,
    }
    return AssistantEvidence(
        provider_payload=payload,
        allowed_citations=frozenset(source_labels),
        source_labels=source_labels,
        source_count=len(source_labels),
        truncated=truncated,
    )
