"""Bounded bilingual Phase 17 inputs."""

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.project_agents.models import AgentRun

MODEL_CHOICES = (
    ("openai/gpt-oss-120b", _("Best quality (120B)")),
    ("openai/gpt-oss-20b", _("Lower cost (20B)")),
)


class AgentRunRequestForm(forms.Form):
    goal_code = forms.ChoiceField(label=_("Goal"), choices=AgentRun.Goal.choices)
    language = forms.ChoiceField(
        label=_("Agent language"), choices=AgentRun.Language.choices
    )
    model_code = forms.ChoiceField(label=_("Model"), choices=MODEL_CHOICES)
    optional_context = forms.CharField(
        label=_("Optional context"),
        required=False,
        max_length=500,
        help_text=_(
            "Add a short project-specific note. It is treated as untrusted "
            "context and cannot grant access or actions."
        ),
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        initial = dict(kwargs.pop("initial", {}))
        initial.setdefault("goal_code", AgentRun.Goal.PROJECT_RECOVERY)
        initial.setdefault("language", actor.preferred_language)
        initial.setdefault("model_code", "openai/gpt-oss-120b")
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )


class ProposalDecisionForm(forms.Form):
    reason = forms.CharField(
        label=_("Decision reason"),
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )
