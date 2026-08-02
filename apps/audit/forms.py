"""Allowlisted Phase 14 audit filters."""

from datetime import timedelta
from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.policies import MAX_AUDIT_RANGE_DAYS, TARGET_TYPES_BY_SCOPE
from apps.audit.presentation import action_label, target_type_label
from apps.audit.selectors import permitted_audit_scopes


class AuditFilterForm(forms.Form):
    scope = forms.ChoiceField(label=_("Scope"), required=False)
    action = forms.ChoiceField(label=_("Action"), required=False)
    target_type = forms.ChoiceField(label=_("Target type"), required=False)
    query = forms.CharField(
        label=_("Search actor or target"),
        required=False,
        max_length=100,
    )
    correlation_id = forms.RegexField(
        label=_("Correlation ID"),
        required=False,
        max_length=64,
        regex=r"^[A-Za-z0-9._-]+$",
    )
    date_from = forms.DateField(
        label=_("From date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        label=_("To date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, actor: User, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        scopes = permitted_audit_scopes(actor)
        scope_field = cast(forms.ChoiceField, self.fields["scope"])
        scope_field.choices = (
            ("", _("All permitted scopes")),
            *((scope, AuditEvent.Scope(scope).label) for scope in scopes),
        )
        action_field = cast(forms.ChoiceField, self.fields["action"])
        action_field.choices = (
            ("", _("All actions")),
            *((code, action_label(code)) for code in actions.ALL_ACTION_CODES),
        )
        target_types = sorted(
            {
                target_type
                for scope in scopes
                for target_type in TARGET_TYPES_BY_SCOPE[scope]
            }
        )
        target_field = cast(forms.ChoiceField, self.fields["target_type"])
        target_field.choices = (
            ("", _("All target types")),
            *(
                (target_type, target_type_label(target_type))
                for target_type in target_types
            ),
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start = cleaned.get("date_from")
        end = cleaned.get("date_to")
        if start is None or end is None:
            return cleaned
        if end < start:
            raise ValidationError(_("The end date cannot precede the start date."))
        if end - start > timedelta(days=MAX_AUDIT_RANGE_DAYS):
            raise ValidationError(
                _("Select a date range of %(days)s days or fewer."),
                params={"days": MAX_AUDIT_RANGE_DAYS},
            )
        scope = cast(str, cleaned.get("scope", ""))
        target_type = cast(str, cleaned.get("target_type", ""))
        if scope and target_type not in ("", *TARGET_TYPES_BY_SCOPE[scope]):
            self.add_error(
                "target_type",
                _("The target type is not available in the selected scope."),
            )
        return cleaned


def default_audit_filter_data() -> dict[str, object]:
    today = timezone.localdate()
    return {
        "date_from": today - timedelta(days=30),
        "date_to": today,
    }
