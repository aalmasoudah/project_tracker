"""Localized notification preference form."""

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import preference_values


class NotificationPreferencesForm(forms.Form):
    task_assignment_in_app = forms.BooleanField(
        label=_("Task assignment in-app notifications"), required=False
    )
    task_assignment_email = forms.BooleanField(
        label=_("Task assignment email notifications"), required=False
    )
    approval_in_app = forms.BooleanField(
        label=_("Approval in-app notifications"),
        required=False,
        disabled=True,
        help_text=_("Approval in-app notifications are mandatory."),
    )
    approval_email = forms.BooleanField(
        label=_("Approval email notifications"), required=False
    )
    deadline_in_app = forms.BooleanField(
        label=_("Deadline and overdue in-app notifications"), required=False
    )
    deadline_email = forms.BooleanField(
        label=_("Deadline and overdue email notifications"), required=False
    )
    mention_in_app = forms.BooleanField(
        label=_("Mention in-app notifications"), required=False
    )
    mention_email = forms.BooleanField(
        label=_("Mention email notifications"), required=False
    )

    def __init__(self, *args: Any, recipient: User, **kwargs: Any) -> None:
        values = preference_values(recipient)
        initial = dict(kwargs.pop("initial", {}))
        for category in Notification.Category.values:
            in_app, email = values[category]
            initial.setdefault(f"{category}_in_app", in_app)
            initial.setdefault(f"{category}_email", email)
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-check-input")

    def preference_values(self) -> dict[str, tuple[bool, bool]]:
        return {
            category: (
                bool(self.cleaned_data[f"{category}_in_app"]),
                bool(self.cleaned_data[f"{category}_email"]),
            )
            for category in Notification.Category.values
        }
