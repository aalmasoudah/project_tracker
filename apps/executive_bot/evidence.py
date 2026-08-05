"""Bounded CEO report evidence with a strict personal-data split."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from django.conf import settings
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.attendance.models import AttendanceEntry, AttendanceSubmission
from apps.attendance.selectors import submissions_visible_to
from apps.courses.models import Course
from apps.executive_bot.models import ExecutiveReportRequest
from apps.projects.models import Project
from apps.reports.datasets import ReportDocument
from apps.reports.dates import format_dual_date
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to

LANGUAGE_CODE: Final = "ar"


@dataclass(frozen=True, slots=True)
class ExecutiveEvidence:
    provider_payload: dict[str, object]
    allowed_citations: frozenset[str]
    source_labels: dict[str, str]
    document: ReportDocument
    source_count: int
    truncated: bool


def _owner_context(task: Task) -> tuple[str, str]:
    if task.project_id:
        assert task.project is not None
        return task.project.code, task.project.localized_name(LANGUAGE_CODE)
    assert task.course is not None
    return task.course.code, task.course.localized_name(LANGUAGE_CODE)


def _active_task_queryset(actor: User) -> QuerySet[Task]:
    priority_order = Case(
        When(priority=Task.Priority.CRITICAL, then=Value(0)),
        When(priority=Task.Priority.HIGH, then=Value(1)),
        When(priority=Task.Priority.MEDIUM, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    return (
        tasks_visible_to(actor)
        .exclude(status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
        .filter(
            Q(
                project__isnull=False,
                project__is_archived=False,
            )
            | Q(
                course__isnull=False,
                course__is_archived=False,
                course__project__is_archived=False,
            )
        )
        .exclude(project__status=Project.Status.CANCELLED)
        .exclude(course__status=Course.Status.CANCELLED)
        .exclude(course__project__status=Project.Status.CANCELLED)
        .annotate(_priority_order=priority_order)
        .order_by("_priority_order", "due_date", "code")
    )


def _task_evidence(*, actor: User, report_type: str) -> ExecutiveEvidence:
    today = timezone.localdate()
    queryset = _active_task_queryset(actor)
    if report_type == ExecutiveReportRequest.ReportType.OVERDUE_TASKS:
        queryset = queryset.filter(due_date__lt=today)
        title = str(_("Overdue task report"))
        filename_stem = "telegram-overdue-tasks"
    else:
        title = str(_("Current task report"))
        filename_stem = "telegram-current-tasks"
    max_rows = int(settings.EXECUTIVE_BOT_REPORT_MAX_ROWS)
    selected = list(queryset[: max_rows + 1])
    truncated = len(selected) > max_rows
    tasks = selected[:max_rows]
    rows: list[tuple[str, ...]] = []
    items: list[dict[str, object]] = []
    source_labels: dict[str, str] = {}
    status_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    ai_limit = min(int(settings.AI_BRIEFING_MAX_EVIDENCE), max_rows)
    for index, task in enumerate(tasks):
        owner_code, owner_name = _owner_context(task)
        due_date = (
            format_dual_date(task.due_date, LANGUAGE_CODE)
            if task.due_date is not None
            else str(_("No due date"))
        )
        days_overdue = (
            str((today - task.due_date).days)
            if task.due_date is not None and task.due_date < today
            else "0"
        )
        rows.append(
            (
                task.code,
                task.localized_name(LANGUAGE_CODE),
                f"{owner_code} - {owner_name}",
                str(task.get_status_display()),
                str(task.get_priority_display()),
                due_date,
                days_overdue,
            )
        )
        status_counts[task.status] += 1
        priority_counts[task.priority] += 1
        if index < ai_limit:
            source_ref = f"task:{task.pk}"
            label = f"{task.code} - {task.localized_name(LANGUAGE_CODE)}"
            source_labels[source_ref] = label
            items.append(
                {
                    "source_ref": source_ref,
                    "code": task.code,
                    "name": task.localized_name(LANGUAGE_CODE),
                    "owner": owner_code,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "days_overdue": int(days_overdue),
                }
            )
    payload: dict[str, object] = {
        "report_type": report_type,
        "as_of_date": today.isoformat(),
        "totals": {
            "tasks": len(tasks),
            "by_status": dict(sorted(status_counts.items())),
            "by_priority": dict(sorted(priority_counts.items())),
            "truncated": truncated,
        },
        "items": items,
    }
    return ExecutiveEvidence(
        provider_payload=payload,
        allowed_citations=frozenset(source_labels),
        source_labels=source_labels,
        document=ReportDocument(
            title=title,
            subtitle=str(_("As of %(date)s"))
            % {"date": format_dual_date(today, LANGUAGE_CODE)},
            headers=(
                str(_("Code")),
                str(_("Task")),
                str(_("Owner context")),
                str(_("Status")),
                str(_("Priority")),
                str(_("Due date")),
                str(_("Days overdue")),
            ),
            rows=tuple(rows),
            filename_stem=filename_stem,
            sheet_name=title[:31],
        ),
        source_count=len(tasks),
        truncated=truncated or len(tasks) > ai_limit,
    )


def _attendance_evidence(*, actor: User, window_days: int) -> ExecutiveEvidence:
    today = timezone.localdate()
    start = today - timedelta(days=window_days - 1)
    submissions = submissions_visible_to(actor).filter(
        state=AttendanceSubmission.State.APPROVED,
        session__start_at__date__gte=start,
        session__start_at__date__lte=today,
    )
    queryset = (
        AttendanceEntry.objects.filter(submission__in=submissions)
        .select_related(
            "submission__session__course",
            "participant__enrollment__trainee",
        )
        .order_by(
            "submission__session__start_at",
            "submission__session__course__code",
            "participant__enrollment__trainee__full_name",
            "pk",
        )
    )
    max_rows = int(settings.EXECUTIVE_BOT_REPORT_MAX_ROWS)
    selected = list(queryset[: max_rows + 1])
    truncated = len(selected) > max_rows
    entries = selected[:max_rows]
    rows: list[tuple[str, ...]] = []
    course_counts: dict[int, Counter[str]] = defaultdict(Counter)
    course_labels: dict[int, tuple[str, str]] = {}
    for entry in entries:
        session = entry.submission.session
        course = session.course
        trainee = entry.participant.enrollment.trainee
        rows.append(
            (
                trainee.full_name,
                course.code,
                course.localized_name(LANGUAGE_CODE),
                session.localized_title(LANGUAGE_CODE),
                format_dual_date(session.start_at.date(), LANGUAGE_CODE),
                str(entry.get_value_display()),
            )
        )
        course_counts[course.pk][entry.value] += 1
        course_counts[course.pk]["total"] += 1
        course_labels[course.pk] = (
            course.code,
            course.localized_name(LANGUAGE_CODE),
        )
    aggregate_items: list[dict[str, object]] = []
    source_labels: dict[str, str] = {}
    overall: Counter[str] = Counter()
    for course_id in sorted(course_counts):
        counts = course_counts[course_id]
        overall.update(counts)
        course_code, course_name = course_labels[course_id]
        source_ref = f"course-attendance:{course_id}"
        source_labels[source_ref] = f"{course_code} - {course_name}"
        aggregate_items.append(
            {
                "source_ref": source_ref,
                "course_code": course_code,
                "course_name": course_name,
                "total": counts["total"],
                "present": counts[AttendanceEntry.Value.PRESENT],
                "absent": counts[AttendanceEntry.Value.ABSENT],
                "late": counts[AttendanceEntry.Value.LATE],
                "excused": counts[AttendanceEntry.Value.EXCUSED],
            }
        )
    payload: dict[str, object] = {
        "report_type": ExecutiveReportRequest.ReportType.ATTENDANCE,
        "date_from": start.isoformat(),
        "date_to": today.isoformat(),
        "totals": {
            "entries": overall["total"],
            "present": overall[AttendanceEntry.Value.PRESENT],
            "absent": overall[AttendanceEntry.Value.ABSENT],
            "late": overall[AttendanceEntry.Value.LATE],
            "excused": overall[AttendanceEntry.Value.EXCUSED],
            "truncated": truncated,
        },
        "courses": aggregate_items,
    }
    return ExecutiveEvidence(
        provider_payload=payload,
        allowed_citations=frozenset(source_labels),
        source_labels=source_labels,
        document=ReportDocument(
            title=str(_("Named trainee attendance report")),
            subtitle=f"{format_dual_date(start, LANGUAGE_CODE)} - "
            f"{format_dual_date(today, LANGUAGE_CODE)}",
            headers=(
                str(_("Trainee")),
                str(_("Course code")),
                str(_("Course")),
                str(_("Session")),
                str(_("Date")),
                str(_("Attendance")),
            ),
            rows=tuple(rows),
            filename_stem="telegram-named-attendance",
            sheet_name=str(_("Trainee attendance"))[:31],
        ),
        source_count=len(entries),
        truncated=truncated,
    )


def build_executive_evidence(
    *, actor: User, report_type: str, window_days: int
) -> ExecutiveEvidence:
    if report_type == ExecutiveReportRequest.ReportType.ATTENDANCE:
        return _attendance_evidence(actor=actor, window_days=window_days)
    return _task_evidence(actor=actor, report_type=report_type)


def critical_tasks_for(actor: User) -> QuerySet[Task]:
    return _active_task_queryset(actor).filter(
        priority=Task.Priority.CRITICAL,
        due_date__isnull=False,
        due_date__lte=timezone.localdate() + timedelta(days=1),
    )
