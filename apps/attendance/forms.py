"""Localized internal, external, review, and correction forms."""

from typing import Any, cast

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.attendance.models import (
    AttendanceEntry,
    AttendanceSubmission,
    Session,
    SessionParticipant,
)
from apps.attendance.policies import DEFAULT_LINK_HOURS, MAX_DECISION_REASON_LENGTH
from apps.courses.models import Course, Trainer


def _style(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            field.widget.attrs.setdefault("class", "form-select")
        elif not isinstance(field.widget, (forms.RadioSelect, forms.FileInput)):
            field.widget.attrs.setdefault("class", "form-control")


class SessionForm(forms.Form):
    course = forms.ModelChoiceField(label=_("Course"), queryset=Course.objects.none())
    trainer = forms.ModelChoiceField(
        label=_("Trainer"), queryset=Trainer.objects.none()
    )
    title_ar = forms.CharField(label=_("Arabic title"), max_length=200)
    title_en = forms.CharField(label=_("English title"), max_length=200)
    start_at = forms.DateTimeField(
        label=_("Starts at"),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    end_at = forms.DateTimeField(
        label=_("Ends at"),
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    recurrence = forms.ChoiceField(
        label=_("Recurrence"), choices=Session.Recurrence.choices
    )
    recurrence_count = forms.IntegerField(
        label=_("Occurrences"), min_value=1, max_value=52, initial=1
    )
    notes = forms.CharField(
        label=_("Notes"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        courses = Course.objects.filter(
            is_archived=False, project__is_archived=False
        ).exclude(status=Course.Status.COMPLETED)
        if not actor.has_perm("attendance.manage_all_sessions"):
            courses = courses.filter(project__manager=actor)
        course_field = cast("forms.ModelChoiceField[Course]", self.fields["course"])
        course_field.queryset = courses.order_by("code")
        trainer_field = cast("forms.ModelChoiceField[Trainer]", self.fields["trainer"])
        trainer_field.queryset = Trainer.objects.filter(
            is_archived=False,
            course_assignments__course__in=courses,
            course_assignments__removed_at__isnull=True,
        ).distinct()
        _style(self)


class LinkIssueForm(forms.Form):
    lifetime_hours = forms.IntegerField(
        label=_("Link lifetime in hours"),
        min_value=1,
        max_value=336,
        initial=DEFAULT_LINK_HOURS,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _style(self)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data: object, initial: object | None = None) -> list[UploadedFile]:
        single_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [cast(UploadedFile, single_clean(item, initial)) for item in data]
        return [cast(UploadedFile, single_clean(data, initial))]


class AttendanceForm(forms.Form):
    trainer_notes = forms.CharField(
        label=_("Trainer notes"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    evidence = MultipleFileField(label=_("Evidence files"), required=False)

    def __init__(
        self, *args: Any, participants: list[SessionParticipant], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.participants = participants
        for participant in participants:
            suffix = str(participant.pk)
            self.fields[f"value_{suffix}"] = forms.ChoiceField(
                label=_("Attendance"),
                choices=AttendanceEntry.Value.choices,
                widget=forms.RadioSelect,
            )
            self.fields[f"notes_{suffix}"] = forms.CharField(
                label=_("Notes"), max_length=500, required=False
            )
        _style(self)

    def entry_values(self) -> dict[int, tuple[str, str]]:
        return {
            participant.pk: (
                str(self.cleaned_data[f"value_{participant.pk}"]),
                str(self.cleaned_data[f"notes_{participant.pk}"]),
            )
            for participant in self.participants
        }


class RejectionForm(forms.Form):
    reason = forms.CharField(
        label=_("Rejection reason"),
        max_length=MAX_DECISION_REASON_LENGTH,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _style(self)


class CorrectionForm(forms.Form):
    reason = forms.CharField(
        label=_("Correction reason"),
        max_length=MAX_DECISION_REASON_LENGTH,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(
        self,
        *args: Any,
        submission: AttendanceSubmission,
        participants: list[SessionParticipant],
        **kwargs: Any,
    ) -> None:
        current = {entry.participant_id: entry for entry in submission.entries.all()}
        initial = dict(kwargs.pop("initial", {}))
        for participant in participants:
            entry = current[participant.pk]
            initial.setdefault(f"value_{participant.pk}", entry.value)
            initial.setdefault(f"notes_{participant.pk}", entry.notes)
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.participants = participants
        for participant in participants:
            suffix = str(participant.pk)
            self.fields[f"value_{suffix}"] = forms.ChoiceField(
                label=_("Attendance"),
                choices=AttendanceEntry.Value.choices,
                widget=forms.RadioSelect,
            )
            self.fields[f"notes_{suffix}"] = forms.CharField(
                label=_("Notes"), max_length=500, required=False
            )
        _style(self)

    def entry_values(self) -> dict[int, tuple[str, str]]:
        return {
            participant.pk: (
                str(self.cleaned_data[f"value_{participant.pk}"]),
                str(self.cleaned_data[f"notes_{participant.pk}"]),
            )
            for participant in self.participants
        }
