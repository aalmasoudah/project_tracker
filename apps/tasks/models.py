"""Approved Phase 5 task and collaboration models."""

from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import normalize_account_search
from apps.projects.models import CODE_VALIDATOR
from apps.tasks.policies import MAX_TASK_DEPTH


class ProtectedTaskQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    """Reject hard deletion of Phase 5 business records."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Phase 5 business records cannot be hard-deleted.")


class Task(models.Model):
    """A project or course task with a bounded hierarchy."""

    class Status(models.TextChoices):
        TODO = "todo", _("To Do")
        IN_PROGRESS = "in_progress", _("In Progress")
        BLOCKED = "blocked", _("Blocked")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    code = models.CharField(_("code"), max_length=30, validators=[CODE_VALIDATOR])
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="tasks",
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="tasks",
        blank=True,
        null=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subtasks",
        blank=True,
        null=True,
    )
    name_ar = models.CharField(_("Arabic name"), max_length=250)
    name_en = models.CharField(_("English name"), max_length=250)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        _("priority"),
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    start_date = models.DateField(_("start date"), blank=True, null=True)
    due_date = models.DateField(_("due date"), blank=True, null=True)
    estimated_hours = models.DecimalField(
        _("estimated hours"),
        max_digits=9,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    actual_hours = models.DecimalField(
        _("actual hours"),
        max_digits=9,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    blocking_reason = models.TextField(_("blocking reason"), blank=True)
    search_key = models.CharField(max_length=1000, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_tasks",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(Lower("code"), name="tasks_task_code_ci_unique"),
            models.CheckConstraint(
                condition=(
                    models.Q(project__isnull=False, course__isnull=True)
                    | models.Q(project__isnull=True, course__isnull=False)
                ),
                name="tasks_task_exactly_one_owner",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(start_date__isnull=True)
                    | models.Q(due_date__isnull=True)
                    | models.Q(due_date__gte=models.F("start_date"))
                ),
                name="tasks_task_dates_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="blocked", blocking_reason__gt="")
                    | ~models.Q(status="blocked")
                ),
                name="tasks_task_blocking_reason_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "todo",
                        "in_progress",
                        "blocked",
                        "completed",
                        "cancelled",
                    )
                ),
                name="tasks_task_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=("low", "medium", "high", "critical")),
                name="tasks_task_priority_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        is_archived=False,
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                    )
                    | models.Q(
                        is_archived=True,
                        archived_at__isnull=False,
                        archived_by__isnull=False,
                    )
                ),
                name="tasks_task_archive_state_valid",
            ),
        ]
        permissions = (
            ("view_all_tasks", "Can view all tasks"),
            ("view_managed_tasks", "Can view managed tasks"),
            ("view_context_tasks", "Can view context tasks"),
            ("view_assigned_tasks", "Can view assigned tasks"),
            ("update_assigned_task", "Can update assigned tasks"),
            ("manage_task_assignments", "Can manage task assignments"),
            ("comment_task", "Can comment on tasks"),
            ("upload_task_file", "Can upload task files"),
            ("archive_task", "Can archive tasks"),
            ("restore_task", "Can restore tasks"),
            ("view_task_history", "Can view task history"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Tasks cannot be hard-deleted.")

    def clean(self) -> None:
        self._normalize_fields()
        super().clean()
        errors = {}
        if bool(self.project_id) == bool(self.course_id):
            errors["project"] = _("Select exactly one project or course.")
        if self.start_date and self.due_date and self.due_date < self.start_date:
            errors["due_date"] = _("Due date cannot precede start date.")
        if self.status == self.Status.BLOCKED and not self.blocking_reason:
            errors["blocking_reason"] = _("A blocking reason is required.")
        if self.parent_id:
            parent = self.parent
            assert parent is not None
            if self.pk and self.parent_id == self.pk:
                errors["parent"] = _("A task cannot be its own parent.")
            elif (
                parent.project_id != self.project_id
                or parent.course_id != self.course_id
            ):
                errors["parent"] = _("Parent and subtask must share an owner.")
            else:
                ancestor: Task | None = parent
                seen: set[int] = set()
                depth = 1
                while ancestor is not None:
                    if (self.pk and ancestor.pk == self.pk) or ancestor.pk in seen:
                        errors["parent"] = _("Task hierarchy cannot contain a cycle.")
                        break
                    seen.add(ancestor.pk)
                    depth += 1
                    ancestor = ancestor.parent
                if "parent" not in errors and depth > MAX_TASK_DEPTH:
                    errors["parent"] = _("Maximum task depth is three levels.")
        if errors:
            raise ValidationError(errors)

    def depth(self) -> int:
        depth = 1
        ancestor = self.parent
        seen: set[int] = set()
        while ancestor is not None:
            if ancestor.pk in seen:
                raise ValidationError(_("Task hierarchy cannot contain a cycle."))
            seen.add(ancestor.pk)
            depth += 1
            ancestor = ancestor.parent
        return depth

    def _normalize_fields(self) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.blocking_reason = self.blocking_reason.strip()
        owner_code = ""
        if self.project_id:
            project = self.project
            assert project is not None
            owner_code = project.code
        elif self.course_id:
            course = self.course
            assert course is not None
            owner_code = course.code
        self.search_key = normalize_account_search(
            f"{self.code} {owner_code} {self.name_ar} {self.name_en}"
        )

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_assignments",
    )
    is_primary = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="removed_task_assignments",
        blank=True,
        null=True,
    )
    removed_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("task", "user"),
                condition=models.Q(removed_at__isnull=True),
                name="tasks_assignment_one_active",
            ),
            models.UniqueConstraint(
                fields=("task",),
                condition=models.Q(removed_at__isnull=True, is_primary=True),
                name="tasks_assignment_one_primary",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(removed_at__isnull=True, removed_by__isnull=True)
                    | models.Q(removed_at__isnull=False, removed_by__isnull=False)
                ),
                name="tasks_assignment_removal_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.task.code}:{self.user.username}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Task assignment history cannot be deleted.")


class Tag(models.Model):
    code = models.CharField(_("code"), max_length=30, validators=[CODE_VALIDATOR])
    name_ar = models.CharField(_("Arabic name"), max_length=100)
    name_en = models.CharField(_("English name"), max_length=100)
    search_key = models.CharField(max_length=300, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_task_tags",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_task_tags",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(Lower("code"), name="tasks_tag_code_ci_unique"),
            models.CheckConstraint(
                condition=(
                    models.Q(is_archived=False, archived_at__isnull=True)
                    | models.Q(is_archived=True, archived_at__isnull=False)
                ),
                name="tasks_tag_archive_state_valid",
            ),
        ]
        permissions = (
            ("archive_tag", "Can archive task tags"),
            ("restore_tag", "Can restore task tags"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.search_key = normalize_account_search(
            f"{self.code} {self.name_ar} {self.name_en}"
        )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Tags cannot be hard-deleted.")

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class TaskTag(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="tag_links")
    tag = models.ForeignKey(Tag, on_delete=models.PROTECT, related_name="task_links")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="added_task_tags",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="removed_task_tags",
        blank=True,
        null=True,
    )
    removed_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("task", "tag"),
                condition=models.Q(removed_at__isnull=True),
                name="tasks_tasktag_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(removed_at__isnull=True, removed_by__isnull=True)
                    | models.Q(removed_at__isnull=False, removed_by__isnull=False)
                ),
                name="tasks_tasktag_removal_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.task.code}:{self.tag.code}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Task tag history cannot be deleted.")


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_comments",
    )
    body = models.TextField(_("comment"), max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        ordering = ("created_at", "pk")

    def __str__(self) -> str:
        return f"{self.task.code}:{self.author.username}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise PermissionDenied("Task comments are immutable.")
        self.body = self.body.strip()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Task comments cannot be deleted.")


def task_file_upload_path(instance: "TaskFile", filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"tasks/{instance.task_id}/{uuid4().hex}{suffix}"


class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="files")
    file = models.FileField(upload_to=task_file_upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=150)
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_task_files",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedTaskQuerySet.as_manager()

    class Meta:
        ordering = ("-uploaded_at", "-pk")

    def __str__(self) -> str:
        return f"{self.task.code}:{self.original_name}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Task files cannot be deleted.")
