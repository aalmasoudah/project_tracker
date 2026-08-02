"""Approved report catalog and format/permission policy."""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

PROJECT_PROGRESS = "project_progress"
OVERDUE_TASKS = "overdue_tasks"
COURSE_ATTENDANCE = "course_attendance"
PROJECT_ATTENDANCE = "project_attendance"
PDF = "pdf"
XLSX = "xlsx"

MAX_REPORT_ROWS = 5_000
MAX_REPORT_RANGE_DAYS = 366


@dataclass(frozen=True)
class ReportDefinition:
    code: str
    label: object
    permission: str
    formats: tuple[str, ...]
    requires_project: bool = False
    requires_course: bool = False


REPORT_DEFINITIONS = (
    ReportDefinition(
        PROJECT_PROGRESS,
        _("Project progress"),
        "reports.export_project_progress",
        (PDF, XLSX),
    ),
    ReportDefinition(
        OVERDUE_TASKS,
        _("Overdue tasks"),
        "reports.export_overdue_tasks",
        (XLSX,),
    ),
    ReportDefinition(
        COURSE_ATTENDANCE,
        _("Course attendance summary"),
        "reports.export_course_attendance",
        (PDF, XLSX),
        requires_course=True,
    ),
    ReportDefinition(
        PROJECT_ATTENDANCE,
        _("Project attendance summary"),
        "reports.export_project_attendance",
        (PDF, XLSX),
        requires_project=True,
    ),
)

REPORT_BY_CODE = {definition.code: definition for definition in REPORT_DEFINITIONS}


def reports_available_to(actor: User) -> tuple[ReportDefinition, ...]:
    return tuple(
        definition
        for definition in REPORT_DEFINITIONS
        if actor.has_perm(definition.permission)
    )
