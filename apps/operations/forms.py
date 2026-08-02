"""Allowlisted archive-center filters."""

from typing import Any, cast

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.operations.selectors import archive_types_available_to


class ArchiveFilterForm(forms.Form):
    record_type = forms.ChoiceField(label=_("Record type"))
    query = forms.CharField(
        label=_("Search archived records"),
        required=False,
        max_length=100,
    )

    def __init__(self, actor: User, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        record_type = cast(forms.ChoiceField, self.fields["record_type"])
        record_type.choices = tuple(
            (definition.code, definition.label)
            for definition in archive_types_available_to(actor)
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
