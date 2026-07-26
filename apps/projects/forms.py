"""Localized Phase 3 project and reference forms."""

from typing import Any, ClassVar, cast

from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.roles import (
    CONTRACTOR,
    EMPLOYEE,
    PROJECT_MANAGER,
    SUPERVISOR,
)
from apps.organizations.models import Department
from apps.projects.models import CODE_VALIDATOR, Category, Client, Project
from apps.projects.policies import STATUS_TRANSITIONS


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, forms.SelectMultiple):
            field.widget.attrs.setdefault("class", "form-select")
            field.widget.attrs.setdefault("size", "8")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class ReferenceForm(forms.Form):
    """Validate bilingual client/category reference data."""

    code = forms.CharField(label=_("Code"), max_length=30, validators=[CODE_VALIDATOR])
    name_ar = forms.CharField(label=_("Arabic name"), max_length=150)
    name_en = forms.CharField(label=_("English name"), max_length=150)

    def __init__(
        self,
        *args: Any,
        model_class: type[Client] | type[Category] = Client,
        instance: Client | Category | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.model_class = model_class
        self.instance = instance
        if instance is not None:
            self.initial.update(
                {
                    "code": instance.code,
                    "name_ar": instance.name_ar,
                    "name_en": instance.name_en,
                }
            )
            self.fields["code"].disabled = True
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = self.model_class.objects.filter(code__iexact=code)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A record with this code already exists."))
        return code


class ProjectForm(forms.ModelForm):  # type: ignore[type-arg]
    """Validate project metadata and approved role eligibility."""

    class Meta:
        model = Project
        fields = (
            "code",
            "name_ar",
            "name_en",
            "department",
            "client",
            "category",
            "manager",
            "supervisor",
            "status",
            "priority",
            "start_date",
            "end_date",
            "budget",
            "goals",
            "requirements",
            "notes",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "goals": forms.Textarea(attrs={"rows": 3}),
            "requirements": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        can_manage_all = actor.has_perm("projects.view_all_projects")
        raw_department_id = self.data.get("department") or self.initial.get(
            "department"
        )
        department_id: int | str | None
        if isinstance(raw_department_id, Department):
            department_id = raw_department_id.pk
        elif isinstance(raw_department_id, (int, str)):
            department_id = raw_department_id
        else:
            department_id = None
        if self.instance.pk:
            department_id = self.instance.department_id

        department_field = cast(
            "forms.ModelChoiceField[Department]",
            self.fields["department"],
        )
        department_field.queryset = Department.objects.filter(is_archived=False)
        if not can_manage_all:
            if actor.department_id is None:
                department_field.queryset = Department.objects.none()
            else:
                department_field.queryset = department_field.queryset.filter(
                    pk=actor.department_id
                )
            department_field.disabled = True

        manager_field = cast(
            "forms.ModelChoiceField[User]",
            self.fields["manager"],
        )
        supervisor_field = cast(
            "forms.ModelChoiceField[User]",
            self.fields["supervisor"],
        )
        if department_id is None:
            if can_manage_all:
                manager_field.queryset = User.objects.filter(
                    is_active=True,
                    groups__name=PROJECT_MANAGER,
                ).distinct()
                supervisor_field.queryset = User.objects.filter(
                    is_active=True,
                    groups__name=SUPERVISOR,
                ).distinct()
            else:
                manager_field.queryset = User.objects.none()
                supervisor_field.queryset = User.objects.none()
        else:
            manager_field.queryset = User.objects.filter(
                is_active=True,
                department_id=department_id,
                groups__name=PROJECT_MANAGER,
            ).distinct()
            supervisor_field.queryset = User.objects.filter(
                is_active=True,
                department_id=department_id,
                groups__name=SUPERVISOR,
            ).distinct()
        if not can_manage_all:
            manager_field.queryset = manager_field.queryset.filter(pk=actor.pk)
            manager_field.disabled = True

        for field_name, model in (("client", Client), ("category", Category)):
            field = cast(
                "forms.ModelChoiceField[Client | Category]",
                self.fields[field_name],
            )
            field.queryset = model.objects.filter(is_archived=False)

        status_field = cast(forms.ChoiceField, self.fields["status"])
        if self.instance.pk:
            allowed = (self.instance.status, *STATUS_TRANSITIONS[self.instance.status])
        else:
            allowed = (Project.Status.DRAFT,)
        status_field.choices = [
            choice for choice in Project.Status.choices if choice[0] in allowed
        ]
        if self.instance.pk:
            self.fields["code"].disabled = True
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Project.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A project with this code already exists."))
        return code

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        department = cleaned.get("department")
        manager = cleaned.get("manager")
        supervisor = cleaned.get("supervisor")
        client = cleaned.get("client")
        category = cleaned.get("category")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", _("End date cannot precede start date."))
        if manager and (
            not manager.is_active
            or manager.department_id != getattr(department, "pk", None)
            or not manager.groups.filter(name=PROJECT_MANAGER).exists()
        ):
            self.add_error("manager", _("Select an eligible Project Manager."))
        if supervisor and (
            not supervisor.is_active
            or supervisor.department_id != getattr(department, "pk", None)
            or not supervisor.groups.filter(name=SUPERVISOR).exists()
        ):
            self.add_error("supervisor", _("Select an eligible Supervisor."))
        if manager and supervisor and manager.pk == supervisor.pk:
            self.add_error("supervisor", _("Manager and supervisor must differ."))
        if client and client.is_archived:
            self.add_error("client", _("Archived clients cannot be assigned."))
        if category and category.is_archived:
            self.add_error("category", _("Archived categories cannot be assigned."))
        return cleaned


class TeamForm(forms.Form):
    """Select the approved active department members."""

    members = forms.ModelMultipleChoiceField(
        label=_("Team members"),
        queryset=User.objects.none(),
        required=False,
    )

    def __init__(self, *args: Any, project: Project, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        eligible_roles = (PROJECT_MANAGER, SUPERVISOR, EMPLOYEE, CONTRACTOR)
        role_groups = Group.objects.filter(name__in=eligible_roles)
        member_field = cast(
            "forms.ModelMultipleChoiceField[User]",
            self.fields["members"],
        )
        member_field.queryset = (
            User.objects.filter(
                is_active=True,
                department=project.department,
                groups__in=role_groups,
            )
            .exclude(pk__in=(project.manager_id, project.supervisor_id))
            .distinct()
            .order_by("display_name")
        )
        _style_fields(self)
