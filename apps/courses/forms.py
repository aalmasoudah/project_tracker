"""Localized Phase 4 course, trainer, assignment, and file forms."""

from typing import Any, ClassVar, cast

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.courses.models import Course, Trainer
from apps.courses.policies import COURSE_STATUS_TRANSITIONS
from apps.courses.services import validate_course_file
from apps.projects.models import Project


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class CourseForm(forms.ModelForm):  # type: ignore[type-arg]
    """Validate approved course metadata and project scope."""

    class Meta:
        model = Course
        fields = (
            "code",
            "project",
            "name_ar",
            "name_en",
            "description",
            "delivery_type",
            "location",
            "capacity",
            "start_at",
            "end_at",
            "status",
            "notes",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "end_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        cast(forms.DateTimeField, self.fields["start_at"]).input_formats = [
            "%Y-%m-%dT%H:%M"
        ]
        cast(forms.DateTimeField, self.fields["end_at"]).input_formats = [
            "%Y-%m-%dT%H:%M"
        ]
        project_field = cast(
            "forms.ModelChoiceField[Project]",
            self.fields["project"],
        )
        projects = Project.objects.filter(is_archived=False)
        if not actor.has_perm("courses.view_all_courses"):
            projects = projects.filter(manager=actor)
        project_field.queryset = projects.select_related("manager")
        status_field = cast(forms.ChoiceField, self.fields["status"])
        if self.instance.pk:
            allowed = (
                self.instance.status,
                *COURSE_STATUS_TRANSITIONS[self.instance.status],
            )
            self.fields["code"].disabled = True
            self.fields["project"].disabled = True
        else:
            allowed = (Course.Status.DRAFT,)
        status_field.choices = [
            choice for choice in Course.Status.choices if choice[0] in allowed
        ]
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Course.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A course with this code already exists."))
        return code

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        project = cleaned.get("project")
        start_at = cleaned.get("start_at")
        end_at = cleaned.get("end_at")
        status = cleaned.get("status")
        if start_at and end_at and end_at <= start_at:
            self.add_error("end_at", _("End date and time must be after the start."))
        if project and status == Course.Status.ACTIVE and project.status != "active":
            self.add_error(
                "status", _("Only an active project can contain an active course.")
            )
        return cleaned


class TrainerForm(forms.ModelForm):  # type: ignore[type-arg]
    """Validate external trainer identity and contact data."""

    class Meta:
        model = Trainer
        fields = (
            "code",
            "name_ar",
            "name_en",
            "email",
            "phone",
            "organization",
            "notes",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "email": forms.EmailInput(attrs={"dir": "ltr"}),
            "phone": forms.TextInput(attrs={"dir": "ltr"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["code"].disabled = True
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Trainer.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A trainer with this code already exists."))
        return code

    def clean_email(self) -> str:
        email = cast(str, self.cleaned_data["email"]).strip().lower()
        queryset = Trainer.objects.filter(email__iexact=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A trainer with this email already exists."))
        return email


class CourseTrainerForm(forms.Form):
    """Select active external trainers for one course."""

    trainers = forms.ModelMultipleChoiceField(
        label=_("Trainers"),
        queryset=Trainer.objects.none(),
        required=False,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = cast("forms.ModelMultipleChoiceField[Trainer]", self.fields["trainers"])
        field.queryset = Trainer.objects.filter(is_archived=False).order_by("code")
        field.widget.attrs["size"] = "8"
        _style_fields(self)


class CourseFileForm(forms.Form):
    """Validate one private course file."""

    file = forms.FileField(label=_("File"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["file"].widget.attrs["accept"] = (
            ".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg"
        )
        _style_fields(self)

    def clean_file(self) -> UploadedFile:
        upload = cast(UploadedFile, self.cleaned_data["file"])
        validate_course_file(upload)
        return upload
