"""Localized trainee and import forms."""

from typing import Any, cast

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.courses.models import Course
from apps.trainees.models import CourseEnrollment, ImportRow
from apps.trainees.services import validate_import_file


def _style(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class EnrollmentForm(forms.Form):
    course = forms.ModelChoiceField(label=_("Course"), queryset=Course.objects.none())
    full_name = forms.CharField(label=_("Full name"), max_length=250)
    phone = forms.CharField(
        label=_("Phone"), max_length=40, widget=forms.TextInput(attrs={"dir": "ltr"})
    )
    email = forms.EmailField(
        label=_("Email address"),
        required=False,
        widget=forms.EmailInput(attrs={"dir": "ltr"}),
    )

    def __init__(
        self,
        *args: Any,
        actor: User,
        enrollment: CourseEnrollment | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.enrollment = enrollment
        course_field = cast("forms.ModelChoiceField[Course]", self.fields["course"])
        courses = Course.objects.filter(
            is_archived=False, project__is_archived=False
        ).exclude(status=Course.Status.COMPLETED)
        if not actor.has_perm("trainees.view_all_enrollments"):
            courses = courses.filter(project__manager=actor)
        course_field.queryset = courses.select_related("project").order_by("code")
        if enrollment is not None:
            self.fields["course"].disabled = True
            self.initial.update(
                {
                    "course": enrollment.course,
                    "full_name": enrollment.trainee.full_name,
                    "phone": enrollment.trainee.phone,
                    "email": enrollment.trainee.email,
                }
            )
        _style(self)


class ImportUploadForm(forms.Form):
    course = forms.ModelChoiceField(label=_("Course"), queryset=Course.objects.none())
    file = forms.FileField(label=_("CSV or XLSX file"))

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = cast("forms.ModelChoiceField[Course]", self.fields["course"])
        courses = Course.objects.filter(
            is_archived=False, project__is_archived=False
        ).exclude(status=Course.Status.COMPLETED)
        if not actor.has_perm("trainees.view_all_enrollments"):
            courses = courses.filter(project__manager=actor)
        field.queryset = courses.select_related("project").order_by("code")
        self.fields["file"].widget.attrs["accept"] = ".csv,.xlsx"
        _style(self)

    def clean_file(self) -> UploadedFile:
        upload = cast(UploadedFile, self.cleaned_data["file"])
        validate_import_file(upload)
        return upload


class DuplicateResolutionForm(forms.Form):
    def __init__(self, *args: Any, rows: list[ImportRow], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for row in rows:
            choices = [(ImportRow.Resolution.SKIP, _("Skip"))]
            if row.duplicate_enrollment_id is not None:
                choices.append((ImportRow.Resolution.UPDATE, _("Update")))
            self.fields[f"row_{row.pk}"] = forms.ChoiceField(
                label=_("Row %(row)s") % {"row": row.row_number},
                choices=choices,
                initial=row.resolution or ImportRow.Resolution.SKIP,
                widget=forms.RadioSelect,
            )

    def resolutions(self) -> dict[int, str]:
        return {
            int(name.removeprefix("row_")): str(value)
            for name, value in self.cleaned_data.items()
        }
