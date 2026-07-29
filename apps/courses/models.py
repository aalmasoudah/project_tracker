"""Approved Phase 4 course, trainer, assignment, and file models."""

from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import EmailValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import normalize_account_search
from apps.projects.models import CODE_VALIDATOR


class ProtectedCourseQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    """Reject hard deletion of Phase 4 business records."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Phase 4 business records cannot be hard-deleted.")


class Trainer(models.Model):
    """An external trainer without a system account."""

    code = models.CharField(_("code"), max_length=30, validators=[CODE_VALIDATOR])
    name_ar = models.CharField(_("Arabic name"), max_length=200)
    name_en = models.CharField(_("English name"), max_length=200)
    email = models.EmailField(_("email address"), validators=[EmailValidator()])
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    organization = models.CharField(_("organization"), max_length=200, blank=True)
    notes = models.TextField(_("notes"), blank=True)
    search_key = models.CharField(max_length=700, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_trainers",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_trainers",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_trainers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedCourseQuerySet.as_manager()

    class Meta:
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"), name="courses_trainer_code_ci_unique"
            ),
            models.UniqueConstraint(
                Lower("email"), name="courses_trainer_email_ci_unique"
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
                name="courses_trainer_archive_state_valid",
            ),
        ]
        permissions = (
            ("archive_trainer", "Can archive trainers"),
            ("restore_trainer", "Can restore trainers"),
            ("view_trainer_contact", "Can view trainer contact data"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Trainers cannot be hard-deleted.")

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
        self.email = self.email.strip().lower()
        self.phone = self.phone.strip()
        self.organization = self.organization.strip()
        self.search_key = normalize_account_search(
            f"{self.code} {self.name_ar} {self.name_en} "
            f"{self.email} {self.phone} {self.organization}"
        )

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class Course(models.Model):
    """A scheduled training course owned by one project."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        ON_HOLD = "on_hold", _("On Hold")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Completed")

    class DeliveryType(models.TextChoices):
        IN_PERSON = "in_person", _("In person")
        ONLINE = "online", _("Online")
        HYBRID = "hybrid", _("Hybrid")

    code = models.CharField(_("code"), max_length=30, validators=[CODE_VALIDATOR])
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name=_("project"),
    )
    name_ar = models.CharField(_("Arabic name"), max_length=200)
    name_en = models.CharField(_("English name"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    delivery_type = models.CharField(
        _("delivery type"),
        max_length=16,
        choices=DeliveryType.choices,
    )
    location = models.CharField(_("location"), max_length=250, blank=True)
    capacity = models.PositiveIntegerField(
        _("capacity"),
        validators=[MinValueValidator(1)],
    )
    start_at = models.DateTimeField(_("starts at"))
    end_at = models.DateTimeField(_("ends at"))
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(_("notes"), blank=True)
    search_key = models.CharField(max_length=800, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_courses",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_courses",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedCourseQuerySet.as_manager()

    class Meta:
        ordering = ("code",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("code"), name="courses_course_code_ci_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="courses_course_schedule_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="courses_course_capacity_positive",
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
                name="courses_course_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(delivery_type__in=("in_person", "online", "hybrid")),
                name="courses_course_delivery_type_valid",
            ),
            models.CheckConstraint(
                condition=(models.Q(delivery_type="online") | ~models.Q(location="")),
                name="courses_course_location_valid",
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
                name="courses_course_archive_state_valid",
            ),
        ]
        permissions = (
            ("view_all_courses", "Can view all courses"),
            ("view_managed_courses", "Can view managed courses"),
            ("view_assigned_courses", "Can view assigned courses"),
            ("archive_course", "Can archive courses"),
            ("restore_course", "Can restore courses"),
            ("manage_course_trainers", "Can manage course trainers"),
            ("upload_course_file", "Can upload course files"),
            ("view_course_history", "Can view course history"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Courses cannot be hard-deleted.")

    def clean(self) -> None:
        self._normalize_fields()
        super().clean()
        errors = {}
        if self.end_at and self.start_at and self.end_at <= self.start_at:
            errors["end_at"] = _("End date and time must be after the start.")
        if (
            self.delivery_type
            in (self.DeliveryType.IN_PERSON, self.DeliveryType.HYBRID)
            and not self.location
        ):
            errors["location"] = _("Location is required for this delivery type.")
        if errors:
            raise ValidationError(errors)

    def _normalize_fields(self) -> None:
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.location = self.location.strip()
        project_code = self.project.code if self.project_id else ""
        self.search_key = normalize_account_search(
            f"{self.code} {project_code} {self.name_ar} {self.name_en} {self.location}"
        )

    def localized_name(self, language_code: str) -> str:
        return self.name_ar if language_code == "ar" else self.name_en


class CourseTrainerAssignment(models.Model):
    """End-dated assignment history between courses and trainers."""

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="trainer_assignments",
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.PROTECT,
        related_name="course_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_course_trainers",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="removed_course_trainers",
        blank=True,
        null=True,
    )
    removed_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedCourseQuerySet.as_manager()

    class Meta:
        ordering = ("trainer_id", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("course", "trainer"),
                condition=models.Q(removed_at__isnull=True),
                name="courses_assignment_one_active",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(removed_at__isnull=True, removed_by__isnull=True)
                    | models.Q(removed_at__isnull=False, removed_by__isnull=False)
                ),
                name="courses_assignment_removal_state_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code}:{self.trainer.code}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Course trainer history cannot be deleted.")


def course_file_upload_path(instance: "CourseFile", filename: str) -> str:
    """Return a random storage key without trusting the source filename."""
    suffix = Path(filename).suffix.lower()
    return f"courses/{instance.course_id}/{uuid4().hex}{suffix}"


class CourseFile(models.Model):
    """Private immutable course attachment metadata."""

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="files",
    )
    file = models.FileField(upload_to=course_file_upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=150)
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_course_files",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedCourseQuerySet.as_manager()

    class Meta:
        ordering = ("-uploaded_at", "-pk")

    def __str__(self) -> str:
        return f"{self.course.code}:{self.original_name}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Course files cannot be hard-deleted.")
