"""Localized Phase 5 task and collaboration forms."""

from typing import Any, ClassVar, cast

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.courses.models import Course
from apps.projects.models import Project
from apps.tasks.models import Tag, Task
from apps.tasks.policies import TASK_STATUS_TRANSITIONS
from apps.tasks.services import validate_task_file


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class TaskForm(forms.ModelForm):  # type: ignore[type-arg]
    assignees = forms.ModelMultipleChoiceField(
        label=_("Assignees"), queryset=User.objects.none()
    )
    primary_owner = forms.ModelChoiceField(
        label=_("Primary owner"), queryset=User.objects.none()
    )

    class Meta:
        model = Task
        fields = (
            "code",
            "project",
            "course",
            "parent",
            "name_ar",
            "name_en",
            "description",
            "status",
            "priority",
            "start_date",
            "due_date",
            "estimated_hours",
            "actual_hours",
            "blocking_reason",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "blocking_reason": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args: Any, actor: User, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        all_contexts = actor.has_perm("tasks.view_all_tasks")
        projects = Project.objects.filter(is_archived=False)
        courses = Course.objects.filter(is_archived=False, project__is_archived=False)
        if not all_contexts:
            projects = projects.filter(manager=actor)
            courses = courses.filter(project__manager=actor)
        cast(
            "forms.ModelChoiceField[Project]", self.fields["project"]
        ).queryset = projects
        cast("forms.ModelChoiceField[Course]", self.fields["course"]).queryset = courses

        project_id = (
            self.data.get("project")
            or getattr(self.instance, "project_id", None)
            or self.initial.get("project")
        )
        course_id = (
            self.data.get("course")
            or getattr(self.instance, "course_id", None)
            or self.initial.get("course")
        )
        project: Project | None = None
        if project_id:
            project = Project.objects.filter(pk=project_id).first()
        elif course_id:
            course = (
                Course.objects.select_related("project").filter(pk=course_id).first()
            )
            project = course.project if course else None
        eligible = User.objects.none()
        if project:
            eligible = (
                User.objects.filter(is_active=True)
                .filter(
                    Q(pk=project.manager_id)
                    | Q(pk=project.supervisor_id)
                    | Q(
                        project_memberships__project=project,
                        project_memberships__removed_at__isnull=True,
                    )
                )
                .distinct()
                .order_by("display_name")
            )
        elif projects.exists():
            eligible = (
                User.objects.filter(is_active=True)
                .filter(
                    Q(pk__in=projects.values("manager_id"))
                    | Q(pk__in=projects.values("supervisor_id"))
                    | Q(
                        project_memberships__project__in=projects,
                        project_memberships__removed_at__isnull=True,
                    )
                )
                .distinct()
                .order_by("display_name")
            )
        cast(
            "forms.ModelMultipleChoiceField[User]", self.fields["assignees"]
        ).queryset = eligible
        cast(
            "forms.ModelChoiceField[User]", self.fields["primary_owner"]
        ).queryset = eligible

        parents = Task.objects.filter(is_archived=False)
        if project_id:
            parents = parents.filter(project_id=project_id, course__isnull=True)
        elif course_id:
            parents = parents.filter(course_id=course_id, project__isnull=True)
        else:
            parents = parents.filter(Q(project__in=projects) | Q(course__in=courses))
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
            self.fields["code"].disabled = True
            self.fields["project"].disabled = True
            self.fields["course"].disabled = True
            current = self.instance.assignments.filter(removed_at__isnull=True)
            self.initial["assignees"] = current.values_list("user_id", flat=True)
            self.initial["primary_owner"] = (
                current.filter(is_primary=True)
                .values_list("user_id", flat=True)
                .first()
            )
        cast("forms.ModelChoiceField[Task]", self.fields["parent"]).queryset = parents

        status_field = cast(forms.ChoiceField, self.fields["status"])
        if self.instance.pk:
            allowed = (
                self.instance.status,
                *TASK_STATUS_TRANSITIONS[self.instance.status],
            )
        else:
            allowed = (Task.Status.TODO,)
        status_field.choices = [
            choice for choice in Task.Status.choices if choice[0] in allowed
        ]
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Task.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A task with this code already exists."))
        return code

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if bool(cleaned.get("project")) == bool(cleaned.get("course")):
            self.add_error("project", _("Select exactly one project or course."))
        assignees = cleaned.get("assignees")
        primary_owner = cleaned.get("primary_owner")
        if assignees is not None and primary_owner not in assignees:
            self.add_error("primary_owner", _("Primary owner must be an assignee."))
        if (
            cleaned.get("start_date")
            and cleaned.get("due_date")
            and cleaned["due_date"] < cleaned["start_date"]
        ):
            self.add_error("due_date", _("Due date cannot precede start date."))
        if cleaned.get("status") == Task.Status.BLOCKED and not cleaned.get(
            "blocking_reason"
        ):
            self.add_error("blocking_reason", _("A blocking reason is required."))
        return cleaned


class AssignedTaskForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Task
        fields = ("status", "actual_hours", "blocking_reason")
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "blocking_reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        allowed = (
            self.instance.status,
            *TASK_STATUS_TRANSITIONS[self.instance.status],
        )
        field = cast(forms.ChoiceField, self.fields["status"])
        field.choices = [
            choice for choice in Task.Status.choices if choice[0] in allowed
        ]
        _style_fields(self)


class TaskCommentForm(forms.Form):
    body = forms.CharField(
        label=_("Comment"),
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _style_fields(self)


class TaskTagForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        label=_("Tags"), queryset=Tag.objects.none(), required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = cast("forms.ModelMultipleChoiceField[Tag]", self.fields["tags"])
        field.queryset = Tag.objects.filter(is_archived=False).order_by("code")
        field.widget.attrs["size"] = "8"
        _style_fields(self)


class TagForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Tag
        fields = ("code", "name_ar", "name_en")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["code"].disabled = True
        _style_fields(self)

    def clean_code(self) -> str:
        code = cast(str, self.cleaned_data["code"]).strip().upper()
        queryset = Tag.objects.filter(code__iexact=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(_("A tag with this code already exists."))
        return code


class TaskFileForm(forms.Form):
    file = forms.FileField(label=_("File"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["file"].widget.attrs["accept"] = (
            ".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg"
        )
        _style_fields(self)

    def clean_file(self) -> UploadedFile:
        upload = cast(UploadedFile, self.cleaned_data["file"])
        validate_task_file(upload)
        return upload
