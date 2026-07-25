"""Localized department forms."""

from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.organizations.models import Department


class DepartmentForm(forms.Form):
    """Create or edit bilingual department data."""

    code = forms.CharField(
        label=_("Department code"),
        max_length=20,
        help_text=_("Use uppercase English letters, numbers, underscores, or hyphens."),
    )
    name_ar = forms.CharField(label=_("Arabic name"), max_length=150)
    name_en = forms.CharField(label=_("English name"), max_length=150)

    def __init__(
        self,
        *args: Any,
        department: Department | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.department = department
        if department is not None:
            self.fields["code"].disabled = True
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Department.objects.filter(code=code)
        if self.department is not None:
            queryset = queryset.exclude(pk=self.department.pk)
        if queryset.exists():
            raise ValidationError(_("A department with this code already exists."))
        return code

    def clean_name_ar(self) -> str:
        value = cast(str, self.cleaned_data["name_ar"]).strip()
        if not value:
            raise ValidationError(_("Arabic name is required."))
        return value

    def clean_name_en(self) -> str:
        value = cast(str, self.cleaned_data["name_en"]).strip()
        if not value:
            raise ValidationError(_("English name is required."))
        return value
