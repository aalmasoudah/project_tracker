"""Build bounded, permission-scoped evidence before any provider call."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.selectors import (
    approval_requests_visible_to,
    milestones_visible_to,
)
from apps.progress.services import project_progress_for
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    source_ref: str
    source_type: str
    source_id: str
    source_label: str
    source_updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    payload: dict[str, object]
    sources: tuple[EvidenceSource, ...]
    fingerprint: str
    truncated: bool

    @property
    def allowed_citations(self) -> frozenset[str]:
        return frozenset(source.source_ref for source in self.sources)


class LocalizedRecord(Protocol):
    def localized_name(self, language_code: str) -> str: ...


def _localized_name(record: LocalizedRecord, language: str) -> str:
    return record.localized_name(language)


def _project_task_filter(project: Project) -> Q:
    return Q(project=project) | Q(course__project=project)


def _project_approval_filter(project: Project) -> Q:
    return (
        Q(project=project)
        | Q(course__project=project)
        | Q(milestone__project=project)
        | Q(task__project=project)
        | Q(task__course__project=project)
    )


def build_project_evidence(
    *,
    actor: User,
    project: Project,
    language: str,
    window_days: int,
) -> EvidenceBundle:
    """Return approved evidence only when the actor can still see the project."""
    if (
        not actor.is_active
        or not projects_visible_to(actor, include_archived=True)
        .filter(pk=project.pk)
        .exists()
    ):
        raise PermissionDenied("Current project access is required.")

    now = timezone.now()
    today = timezone.localdate()
    window_start = now - timedelta(days=window_days)
    window_end = today + timedelta(days=window_days)
    source_limit = int(settings.AI_BRIEFING_MAX_EVIDENCE)

    progress = project_progress_for(actor, project)
    project_ref = f"project:{project.pk}"
    sources: list[EvidenceSource] = [
        EvidenceSource(
            source_ref=project_ref,
            source_type="project",
            source_id=str(project.pk),
            source_label=f"{project.code} — {_localized_name(project, language)}",
            source_updated_at=project.updated_at,
        )
    ]
    records: list[dict[str, object]] = []

    visible_tasks = tasks_visible_to(actor).filter(_project_task_filter(project))
    task_candidates = visible_tasks.exclude(status=Task.Status.CANCELLED).filter(
        Q(status=Task.Status.BLOCKED)
        | Q(due_date__lt=today)
        | Q(due_date__lte=window_end, due_date__gte=today)
        | Q(updated_at__gte=window_start)
    )
    task_candidates = task_candidates.select_related("course").order_by(
        "due_date", "code", "pk"
    )

    visible_milestones = milestones_visible_to(actor).filter(project=project)
    milestone_candidates = visible_milestones.exclude(status="cancelled").filter(
        Q(due_date__lte=window_end) | Q(updated_at__gte=window_start)
    )
    milestone_candidates = milestone_candidates.order_by("due_date", "code", "pk")

    visible_approvals = approval_requests_visible_to(actor).filter(
        _project_approval_filter(project)
    )
    approval_candidates = visible_approvals.filter(
        Q(status__in=("pending_supervisor", "pending_manager"))
        | Q(submitted_at__gte=window_start)
    ).order_by("-submitted_at", "-pk")

    candidate_count = (
        task_candidates.count()
        + milestone_candidates.count()
        + approval_candidates.count()
    )

    def add_record(
        *,
        source_ref: str,
        source_type: str,
        source_id: int,
        source_label: str,
        updated_at: datetime | None,
        record: dict[str, object],
    ) -> bool:
        if len(sources) >= source_limit:
            return False
        sources.append(
            EvidenceSource(
                source_ref=source_ref,
                source_type=source_type,
                source_id=str(source_id),
                source_label=source_label,
                source_updated_at=updated_at,
            )
        )
        records.append(record)
        return True

    for task in task_candidates:
        task_ref = f"task:{task.pk}"
        if not add_record(
            source_ref=task_ref,
            source_type="task",
            source_id=task.pk,
            source_label=f"{task.code} — {_localized_name(task, language)}",
            updated_at=task.updated_at,
            record={
                "source_ref": task_ref,
                "kind": "task",
                "code": task.code,
                "name": _localized_name(task, language),
                "course_code": task.course.code if task.course is not None else None,
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "blocking_reason": task.blocking_reason,
            },
        ):
            break

    if len(sources) < source_limit:
        for milestone in milestone_candidates:
            milestone_ref = f"milestone:{milestone.pk}"
            if not add_record(
                source_ref=milestone_ref,
                source_type="milestone",
                source_id=milestone.pk,
                source_label=(
                    f"{milestone.code} — {_localized_name(milestone, language)}"
                ),
                updated_at=milestone.updated_at,
                record={
                    "source_ref": milestone_ref,
                    "kind": "milestone",
                    "code": milestone.code,
                    "name": _localized_name(milestone, language),
                    "status": milestone.status,
                    "start_date": milestone.start_date.isoformat(),
                    "due_date": milestone.due_date.isoformat(),
                },
            ):
                break

    if len(sources) < source_limit:
        for approval in approval_candidates:
            approval_ref = f"approval:{approval.pk}"
            if not add_record(
                source_ref=approval_ref,
                source_type="approval",
                source_id=approval.pk,
                source_label=f"{approval.target_code} #{approval.attempt}",
                updated_at=approval.resolved_at or approval.submitted_at,
                record={
                    "source_ref": approval_ref,
                    "kind": "approval",
                    "target_type": approval.target_type,
                    "target_code": approval.target_code,
                    "attempt": approval.attempt,
                    "status": approval.status,
                    "submitted_at": approval.submitted_at.isoformat(),
                    "resolved_at": (
                        approval.resolved_at.isoformat()
                        if approval.resolved_at is not None
                        else None
                    ),
                },
            ):
                break

    truncated = candidate_count > len(records)
    payload: dict[str, object] = {
        "as_of_date": today.isoformat(),
        "language": language,
        "window_days": window_days,
        "project": {
            "source_ref": project_ref,
            "code": project.code,
            "name": _localized_name(project, language),
            "status": project.status,
            "priority": project.priority,
            "start_date": project.start_date.isoformat(),
            "end_date": project.end_date.isoformat(),
            "progress_state": str(progress.state)
            if progress is not None
            else "unavailable",
            "progress_percentage": (
                str(progress.percentage) if progress is not None else None
            ),
        },
        "counts": {
            "active_tasks": visible_tasks.exclude(status=Task.Status.CANCELLED).count(),
            "blocked_tasks": visible_tasks.filter(status=Task.Status.BLOCKED).count(),
            "overdue_tasks": visible_tasks.exclude(
                status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED)
            )
            .filter(due_date__lt=today)
            .count(),
            "open_approvals": visible_approvals.filter(
                status__in=("pending_supervisor", "pending_manager")
            ).count(),
        },
        "records": records,
        "truncated": truncated,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return EvidenceBundle(
        payload=payload,
        sources=tuple(sources),
        fingerprint=hashlib.sha256(canonical).hexdigest(),
        truncated=truncated,
    )
