"""Selector-backed, bounded report datasets."""

from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from django.db.models import Count, Q, QuerySet
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.attendance.models import AttendanceEntry, AttendanceSubmission
from apps.attendance.selectors import submissions_visible_to
from apps.courses.models import Course
from apps.progress.services import project_progress_for
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.reports.dates import format_dual_date
from apps.reports.policies import MAX_REPORT_ROWS
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to


class ReportTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class ReportDocument:
    title: str
    subtitle: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    filename_stem: str
    sheet_name: str
    sections: tuple[tuple[str, tuple[str, ...]], ...] = ()
    column_weights: tuple[float, ...] = ()


def _bounded(queryset: QuerySet[Any]) -> tuple[Any, ...]:
    rows = tuple(queryset[: MAX_REPORT_ROWS + 1])
    if len(rows) > MAX_REPORT_ROWS:
        raise ReportTooLargeError(
            _("The report exceeds the maximum of %(rows)s rows.")
            % {"rows": MAX_REPORT_ROWS}
        )
    return rows


def project_progress_document(
    *,
    actor: User,
    project: Project | None,
    language_code: str,
) -> ReportDocument:
    queryset = projects_visible_to(actor)
    if project is not None:
        queryset = queryset.filter(pk=project.pk)
    source = _bounded(queryset)
    rows = []
    for item in source:
        progress = project_progress_for(actor, item)
        progress_value = (
            f"{progress.percentage}%" if progress is not None else str(_("Unavailable"))
        )
        rows.append(
            (
                item.code,
                item.localized_name(language_code),
                str(item.get_status_display()),
                format_dual_date(item.start_date, language_code),
                format_dual_date(item.end_date, language_code),
                progress_value,
            )
        )
    scope = project.code if project is not None else str(_("All permitted projects"))
    return ReportDocument(
        title=str(_("Project progress report")),
        subtitle=scope,
        headers=(
            str(_("Code")),
            str(_("Project")),
            str(_("Status")),
            str(_("Start")),
            str(_("End")),
            str(_("Progress")),
        ),
        rows=tuple(rows),
        filename_stem="project-progress",
        sheet_name=str(_("Project progress"))[:31],
    )


def overdue_tasks_document(
    *,
    actor: User,
    project: Project | None,
    start: date,
    end: date,
    language_code: str,
) -> ReportDocument:
    queryset = (
        tasks_visible_to(actor)
        .filter(
            due_date__isnull=False,
            due_date__gte=start,
            due_date__lte=end,
        )
        .exclude(status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
    )
    if project is not None:
        queryset = queryset.filter(Q(project=project) | Q(course__project=project))
    source = _bounded(queryset)
    rows = []
    for item in source:
        assert item.due_date is not None
        if item.project_id:
            assert item.project is not None
            owner_code = item.project.code
        else:
            assert item.course is not None
            owner_code = item.course.code
        rows.append(
            (
                item.code,
                item.localized_name(language_code),
                owner_code,
                str(item.get_status_display()),
                format_dual_date(item.due_date, language_code),
                str((end - item.due_date).days),
            )
        )
    return ReportDocument(
        title=str(_("Overdue task report")),
        subtitle=f"{format_dual_date(start, language_code)} - "
        f"{format_dual_date(end, language_code)}",
        headers=(
            str(_("Code")),
            str(_("Task")),
            str(_("Owner context")),
            str(_("Status")),
            str(_("Due date")),
            str(_("Days overdue")),
        ),
        rows=tuple(rows),
        filename_stem="overdue-tasks",
        sheet_name=str(_("Overdue tasks"))[:31],
    )


def _approved_submissions(actor: User) -> QuerySet[AttendanceSubmission]:
    return submissions_visible_to(actor).filter(
        state=AttendanceSubmission.State.APPROVED
    )


def _attendance_counts(queryset: QuerySet[Any], *group_fields: str) -> QuerySet[Any]:
    return cast(
        QuerySet[Any],
        queryset.values(*group_fields)
        .annotate(
            total=Count("entries"),
            present=Count(
                "entries",
                filter=Q(entries__value=AttendanceEntry.Value.PRESENT),
            ),
            absent=Count(
                "entries",
                filter=Q(entries__value=AttendanceEntry.Value.ABSENT),
            ),
            late=Count(
                "entries",
                filter=Q(entries__value=AttendanceEntry.Value.LATE),
            ),
            excused=Count(
                "entries",
                filter=Q(entries__value=AttendanceEntry.Value.EXCUSED),
            ),
        )
        .order_by(*group_fields),
    )


def course_attendance_document(
    *,
    actor: User,
    course: Course,
    start: date,
    end: date,
    language_code: str,
) -> ReportDocument:
    queryset = _approved_submissions(actor).filter(
        session__course=course,
        session__start_at__date__gte=start,
        session__start_at__date__lte=end,
    )
    values = _bounded(
        _attendance_counts(
            queryset,
            "session_id",
            "session__title_ar",
            "session__title_en",
            "session__start_at",
        )
    )
    rows = tuple(
        (
            f"S-{item['session_id']}",
            (
                item["session__title_ar"]
                if language_code == "ar"
                else item["session__title_en"]
            ),
            format_dual_date(item["session__start_at"].date(), language_code),
            str(item["total"]),
            str(item["present"]),
            str(item["absent"]),
            str(item["late"]),
            str(item["excused"]),
        )
        for item in values
    )
    return ReportDocument(
        title=str(_("Course attendance summary")),
        subtitle=f"{course.code} - {course.localized_name(language_code)}",
        headers=_attendance_headers(include_code=True),
        rows=rows,
        filename_stem=f"course-attendance-{course.code.lower()}",
        sheet_name=str(_("Course attendance"))[:31],
    )


def project_attendance_document(
    *,
    actor: User,
    project: Project,
    start: date,
    end: date,
    language_code: str,
) -> ReportDocument:
    queryset = _approved_submissions(actor).filter(
        session__course__project=project,
        session__start_at__date__gte=start,
        session__start_at__date__lte=end,
    )
    values = _bounded(
        _attendance_counts(
            queryset,
            "session__course_id",
            "session__course__code",
            "session__course__name_ar",
            "session__course__name_en",
        )
    )
    rows = tuple(
        (
            item["session__course__code"],
            (
                item["session__course__name_ar"]
                if language_code == "ar"
                else item["session__course__name_en"]
            ),
            str(item["total"]),
            str(item["present"]),
            str(item["absent"]),
            str(item["late"]),
            str(item["excused"]),
        )
        for item in values
    )
    return ReportDocument(
        title=str(_("Project attendance summary")),
        subtitle=f"{project.code} - {project.localized_name(language_code)}",
        headers=_attendance_headers(include_code=False),
        rows=rows,
        filename_stem=f"project-attendance-{project.code.lower()}",
        sheet_name=str(_("Project attendance"))[:31],
    )


def _attendance_headers(*, include_code: bool) -> tuple[str, ...]:
    first = str(_("Session")) if include_code else str(_("Course"))
    date_headers = (str(_("Date")),) if include_code else ()
    return (
        first,
        str(_("Name")),
        *date_headers,
        str(_("Total")),
        str(_("Present")),
        str(_("Absent")),
        str(_("Late")),
        str(_("Excused")),
    )
