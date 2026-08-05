"""Validated AI briefing request input."""

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.ai_briefings.models import AIBriefing


class BriefingRequestForm(forms.Form):
    language = forms.ChoiceField(
        label=_("Briefing language"),
        choices=AIBriefing.Language.choices,
    )
    detail_level = forms.ChoiceField(
        label=_("Detail level"),
        choices=AIBriefing.DetailLevel.choices,
    )
    evidence_window_days = forms.TypedChoiceField(
        label=_("Evidence window"),
        choices=AIBriefing.EvidenceWindow.choices,
        coerce=int,
    )

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        initial = dict(kwargs.pop("initial", {}))
        initial.setdefault("language", actor.preferred_language)
        initial.setdefault("detail_level", AIBriefing.DetailLevel.EXECUTIVE)
        initial.setdefault(
            "evidence_window_days",
            AIBriefing.EvidenceWindow.FOURTEEN_DAYS,
        )
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select"
