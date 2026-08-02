"""Allowlisted report request filters."""

from datetime import timedelta
from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.courses.models import Course
from apps.courses.selectors import courses_visible_to
from apps.projects.models import Project
from apps.projects.selectors import projects_visible_to
from apps.reports.policies import (
    MAX_REPORT_RANGE_DAYS,
    OVERDUE_TASKS,
    PDF,
    REPORT_BY_CODE,
    XLSX,
    reports_available_to,
)


class ReportRequestForm(forms.Form):
    report_type = forms.ChoiceField(label=_("Report"))
    output_format = forms.ChoiceField(
        label=_("Format"),
        choices=((PDF, _("PDF")), (XLSX, _("Excel"))),
    )
    project = forms.ModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.none(),
        required=False,
        empty_label=_("All permitted projects"),
    )
    course = forms.ModelChoiceField(
        label=_("Course"),
        queryset=Course.objects.none(),
        required=False,
        empty_label=_("Select a course"),
    )
    date_from = forms.DateField(
        label=_("From date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("To date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    locale = forms.ChoiceField(
        label=_("Report language"),
        choices=(("ar", _("Arabic")), ("en", _("English"))),
    )

    def __init__(self, actor: User, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        report_field = cast(forms.ChoiceField, self.fields["report_type"])
        report_field.choices = tuple(
            (definition.code, definition.label)
            for definition in reports_available_to(actor)
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
        project_field = cast(
            "forms.ModelChoiceField[Project]",
            self.fields["project"],
        )
        project_field.queryset = projects_visible_to(actor)
        course_field = cast(
            "forms.ModelChoiceField[Course]",
            self.fields["course"],
        )
        course_field.queryset = courses_visible_to(actor)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        report_type = cast(str | None, cleaned.get("report_type"))
        definition = (
            REPORT_BY_CODE.get(report_type) if report_type is not None else None
        )
        if definition is None or not self.actor.has_perm(definition.permission):
            raise ValidationError(_("Select a report you are allowed to export."))
        output_format = cleaned.get("output_format")
        if output_format not in definition.formats:
            self.add_error(
                "output_format",
                _("This format is not available for the selected report."),
            )
        project = cleaned.get("project")
        course = cleaned.get("course")
        if definition.requires_project and project is None:
            self.add_error("project", _("Select a project."))
        if definition.requires_course and course is None:
            self.add_error("course", _("Select a course."))

        today = timezone.localdate()
        start = cleaned.get("date_from") or today - timedelta(days=365)
        end = cleaned.get("date_to") or today
        if end < start:
            raise ValidationError(_("The end date cannot precede the start date."))
        if end - start > timedelta(days=MAX_REPORT_RANGE_DAYS):
            raise ValidationError(
                _("Select a date range of %(days)s days or fewer."),
                params={"days": MAX_REPORT_RANGE_DAYS},
            )
        if report_type == OVERDUE_TASKS and end > today:
            end = today
        cleaned["date_from"] = start
        cleaned["date_to"] = end
        return cleaned
