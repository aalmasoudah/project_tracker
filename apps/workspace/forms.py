"""Allowlisted Phase 12 input forms."""

from datetime import date, timedelta
from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.workspace.models import SavedFilter

MAX_QUERY_LENGTH = 100
MAX_RANGE_DAYS = 92


class SearchForm(forms.Form):
    q = forms.CharField(
        label=_("Search"),
        max_length=MAX_QUERY_LENGTH,
        required=False,
        strip=True,
    )

    def clean_q(self) -> str:
        query = cast(str, self.cleaned_data["q"])
        if query and len(query) < 2:
            raise ValidationError(_("Enter at least two characters."))
        return query


class PlanningFilterForm(SearchForm):
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

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        today = timezone.localdate()
        start = cleaned.get("date_from") or today - timedelta(days=15)
        end = cleaned.get("date_to") or today + timedelta(days=45)
        if end < start:
            raise ValidationError(_("The end date cannot precede the start date."))
        if end - start > timedelta(days=MAX_RANGE_DAYS):
            raise ValidationError(
                _("Select a date range of %(days)s days or fewer."),
                params={"days": MAX_RANGE_DAYS},
            )
        cleaned["date_from"] = start
        cleaned["date_to"] = end
        return cleaned


class SavedFilterForm(forms.Form):
    name = forms.CharField(label=_("Filter name"), max_length=100, strip=True)
    view_type = forms.ChoiceField(
        label=_("View"),
        choices=SavedFilter.ViewType.choices,
    )
    q = forms.CharField(max_length=MAX_QUERY_LENGTH, required=False, strip=True)
    date_from = forms.DateField(required=False)
    date_to = forms.DateField(required=False)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        view_type = cleaned.get("view_type")
        query = cleaned.get("q", "")
        if query and len(query) < 2:
            self.add_error("q", _("Enter at least two characters."))
        if view_type in {
            SavedFilter.ViewType.CALENDAR,
            SavedFilter.ViewType.TIMELINE,
            SavedFilter.ViewType.GANTT,
        }:
            planner = PlanningFilterForm(
                {
                    "q": query,
                    "date_from": cleaned.get("date_from"),
                    "date_to": cleaned.get("date_to"),
                }
            )
            if not planner.is_valid():
                raise ValidationError(_("The saved date range is invalid."))
            cleaned["date_from"] = planner.cleaned_data["date_from"]
            cleaned["date_to"] = planner.cleaned_data["date_to"]
        else:
            cleaned["date_from"] = None
            cleaned["date_to"] = None
        return cleaned


def criteria_from_cleaned_data(cleaned_data: dict[str, Any]) -> dict[str, str]:
    """Serialize only the approved fields for the selected view."""
    criteria: dict[str, str] = {}
    query = cleaned_data.get("q")
    if query:
        criteria["q"] = str(query)
    if cleaned_data["view_type"] in {
        SavedFilter.ViewType.CALENDAR,
        SavedFilter.ViewType.TIMELINE,
        SavedFilter.ViewType.GANTT,
    }:
        for key in ("date_from", "date_to"):
            value = cleaned_data.get(key)
            if isinstance(value, date):
                criteria[key] = value.isoformat()
    return criteria
