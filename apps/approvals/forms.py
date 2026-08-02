"""Localized milestone and approval forms."""

from typing import Any, ClassVar, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.approvals.models import Milestone
from apps.approvals.policies import MILESTONE_STATUS_TRANSITIONS
from apps.projects.models import Project


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class MilestoneForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Milestone
        fields = (
            "code",
            "project",
            "name_ar",
            "name_en",
            "description",
            "start_date",
            "due_date",
            "status",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        project_field = cast(
            "forms.ModelChoiceField[Project]",
            self.fields["project"],
        )
        projects = Project.objects.filter(is_archived=False).exclude(
            status__in=(Project.Status.CANCELLED, Project.Status.COMPLETED)
        )
        if not actor.has_perm("approvals.view_all_milestones"):
            projects = projects.filter(manager=actor)
        project_field.queryset = projects.order_by("code")
        status_field = cast(forms.ChoiceField, self.fields["status"])
        if self.instance.pk:
            allowed = (
                self.instance.status,
                *MILESTONE_STATUS_TRANSITIONS[self.instance.status],
            )
            self.fields["code"].disabled = True
            self.fields["project"].disabled = True
        else:
            allowed = (Milestone.Status.DRAFT,)
        status_field.choices = [
            choice for choice in Milestone.Status.choices if choice[0] in allowed
        ]
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Milestone.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A milestone with this code already exists."))
        return code


class RejectionForm(forms.Form):
    reason = forms.CharField(
        label=_("Rejection reason"),
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
    )

    def clean_reason(self) -> str:
        reason = cast(str, self.cleaned_data["reason"]).strip()
        if not reason:
            raise ValidationError(_("A rejection reason is required."))
        return reason
