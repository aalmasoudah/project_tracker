"""Approved Phase 3 project and team models."""

from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import normalize_account_search

CODE_VALIDATOR = RegexValidator(
    regex=r"^[A-Z][A-Z0-9_-]{1,29}$",
    message=_(
        "Use 2-30 uppercase English letters, numbers, underscores, or hyphens, "
        "starting with a letter."
    ),
)


class ProtectedDeleteQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    """Reject bulk hard deletion for Phase 3 business records."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Phase 3 business records cannot be hard-deleted.")


class ArchivedReference(models.Model):
    """Shared storage behavior for approved bilingual reference records."""

    code = models.CharField(
        _("code"),
        max_length=30,
        unique=True,
        validators=[CODE_VALIDATOR],
    )
    name_ar = models.CharField(_("Arabic name"), max_length=150)
    name_en = models.CharField(_("English name"), max_length=150)
    search_key = models.CharField(max_length=350, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = ProtectedDeleteQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ("code",)

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Project reference records cannot be hard-deleted.")

    def clean(self) -> None:
        self._normalize_fields()
        super().clean()
        errors = {}
        if not self.name_ar:
            errors["name_ar"] = _("Arabic name is required.")
        if not self.name_en:
            errors["name_en"] = _("English name is required.")
        if errors:
            raise ValidationError(errors)

    def _normalize_fields(self) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.search_key = normalize_account_search(
            f"{self.code} {self.name_ar} {self.name_en}"
        )

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class Client(ArchivedReference):
    """A project client identified by a stable code."""

    class Meta(ArchivedReference.Meta):
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"),
                name="projects_client_code_ci_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_archived=False, archived_at__isnull=True)
                    | models.Q(is_archived=True, archived_at__isnull=False)
                ),
                name="projects_client_archive_state_valid",
            ),
        ]
        permissions = (
            ("archive_client", "Can archive clients"),
            ("restore_client", "Can restore clients"),
        )


class Category(ArchivedReference):
    """A project classification identified by a stable code."""

    class Meta(ArchivedReference.Meta):
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"),
                name="projects_category_code_ci_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_archived=False, archived_at__isnull=True)
                    | models.Q(is_archived=True, archived_at__isnull=False)
                ),
                name="projects_category_archive_state_valid",
            ),
        ]
        permissions = (
            ("archive_category", "Can archive categories"),
            ("restore_category", "Can restore categories"),
        )


class Project(models.Model):
    """An approved project without progress or completion semantics."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        ON_HOLD = "on_hold", _("On Hold")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Completed")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    code = models.CharField(
        _("code"),
        max_length=30,
        unique=True,
        validators=[CODE_VALIDATOR],
    )
    name_ar = models.CharField(_("Arabic name"), max_length=200)
    name_en = models.CharField(_("English name"), max_length=200)
    search_key = models.CharField(max_length=500, editable=False, db_index=True)
    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name=_("department"),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name=_("client"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="projects",
        blank=True,
        null=True,
        verbose_name=_("category"),
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="managed_projects",
        verbose_name=_("project manager"),
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supervised_projects",
        blank=True,
        null=True,
        verbose_name=_("supervisor"),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    priority = models.CharField(
        _("priority"),
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    budget = models.DecimalField(
        _("budget"),
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="SAR",
        editable=False,
    )
    goals = models.TextField(_("goals"), blank=True)
    requirements = models.TextField(_("requirements"), blank=True)
    notes = models.TextField(_("notes"), blank=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_projects",
        blank=True,
        null=True,
        verbose_name=_("archived by"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
        verbose_name=_("created by"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_projects",
        verbose_name=_("updated by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = ProtectedDeleteQuerySet.as_manager()

    class Meta:
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"),
                name="projects_project_code_ci_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="projects_project_dates_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(budget__isnull=True) | models.Q(budget__gte=0),
                name="projects_project_budget_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "draft",
                        "active",
                        "on_hold",
                        "cancelled",
                        "completed",
                    )
                ),
                name="projects_project_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=("low", "medium", "high", "critical")),
                name="projects_project_priority_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(currency="SAR"),
                name="projects_project_currency_sar",
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
                name="projects_project_archive_state_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(supervisor__isnull=True)
                    | ~models.Q(manager=models.F("supervisor"))
                ),
                name="projects_project_manager_supervisor_distinct",
            ),
        ]
        permissions = (
            ("view_all_projects", "Can view all projects"),
            ("view_managed_projects", "Can view managed projects"),
            ("view_assigned_projects", "Can view assigned projects"),
            ("view_project_budget", "Can view project budgets"),
            ("manage_project_team", "Can manage project teams"),
            ("view_project_history", "Can view project history"),
            ("archive_project", "Can archive projects"),
            ("restore_project", "Can restore projects"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Projects cannot be hard-deleted.")

    def clean(self) -> None:
        self._normalize_fields()
        super().clean()
        errors = {}
        if not self.name_ar:
            errors["name_ar"] = _("Arabic name is required.")
        if not self.name_en:
            errors["name_en"] = _("English name is required.")
        if errors:
            raise ValidationError(errors)

    def _normalize_fields(self) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.search_key = normalize_account_search(
            f"{self.code} {self.name_ar} {self.name_en}"
        )

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class ProjectMembership(models.Model):
    """Timestamped project membership that is removed rather than deleted."""

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_memberships",
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="added_project_memberships",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="removed_project_memberships",
        blank=True,
        null=True,
    )
    removed_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedDeleteQuerySet.as_manager()

    class Meta:
        ordering = ("user_id", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("project", "user"),
                condition=models.Q(removed_at__isnull=True),
                name="projects_membership_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(removed_at__isnull=True, removed_by__isnull=True)
                    | models.Q(removed_at__isnull=False, removed_by__isnull=False)
                ),
                name="projects_membership_removal_state_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("project", "removed_at"),
                name="projects_member_active_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.project.code}:{self.user.username}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Project membership history cannot be deleted.")
