"""Report document dispatch and output generation."""

from datetime import date

from django.utils.translation import override

from apps.accounts.models import User
from apps.courses.models import Course
from apps.projects.models import Project
from apps.reports.datasets import (
    ReportDocument,
    course_attendance_document,
    overdue_tasks_document,
    project_attendance_document,
    project_progress_document,
)
from apps.reports.policies import (
    COURSE_ATTENDANCE,
    OVERDUE_TASKS,
    PDF,
    PROJECT_ATTENDANCE,
    PROJECT_PROGRESS,
    XLSX,
)
from apps.reports.renderers import render_pdf, render_xlsx


def build_report_document(
    *,
    actor: User,
    report_type: str,
    project: Project | None,
    course: Course | None,
    start: date,
    end: date,
    language_code: str,
) -> ReportDocument:
    with override(language_code):
        if report_type == PROJECT_PROGRESS:
            return project_progress_document(
                actor=actor,
                project=project,
                language_code=language_code,
            )
        if report_type == OVERDUE_TASKS:
            return overdue_tasks_document(
                actor=actor,
                project=project,
                start=start,
                end=end,
                language_code=language_code,
            )
        if report_type == COURSE_ATTENDANCE:
            assert course is not None
            return course_attendance_document(
                actor=actor,
                course=course,
                start=start,
                end=end,
                language_code=language_code,
            )
        if report_type == PROJECT_ATTENDANCE:
            assert project is not None
            return project_attendance_document(
                actor=actor,
                project=project,
                start=start,
                end=end,
                language_code=language_code,
            )
    raise ValueError("Unsupported report type.")


def render_report(
    document: ReportDocument,
    *,
    output_format: str,
    language_code: str,
) -> bytes:
    if output_format == PDF:
        return render_pdf(document, language_code=language_code)
    if output_format == XLSX:
        return render_xlsx(document, language_code=language_code)
    raise ValueError("Unsupported report format.")
