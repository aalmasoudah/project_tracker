"""Phase 8 trainee enrollment and immutable import evidence."""

from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.trainees.normalization import (
    normalize_trainee_name,
    normalize_trainee_phone,
    trainee_identity_key,
)


class ProtectedTraineeQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Phase 8 records cannot be hard-deleted.")


class Trainee(models.Model):
    full_name = models.CharField(_("full name"), max_length=250)
    phone = models.CharField(_("phone"), max_length=40)
    email = models.EmailField(_("email address"), blank=True)
    name_key = models.CharField(max_length=300, editable=False, db_index=True)
    phone_key = models.CharField(max_length=20, editable=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_trainees",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_trainees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedTraineeQuerySet.as_manager()

    class Meta:
        ordering = ("full_name", "pk")
        permissions = (("view_trainee_contact", "Can view trainee contact data"),)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=~models.Q(name_key=""),
                name="trainees_name_key_not_blank",
            ),
            models.CheckConstraint(
                condition=~models.Q(phone_key=""),
                name="trainees_phone_key_not_blank",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._normalize_fields()
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Trainees cannot be hard-deleted.")

    def clean(self) -> None:
        self._normalize_fields()
        super().clean()
        errors: dict[str, object] = {}
        if not self.name_key:
            errors["full_name"] = _("Full name is required.")
        if not self.phone_key:
            errors["phone"] = _("Enter a valid phone number.")
        if errors:
            raise ValidationError(errors)

    def _normalize_fields(self) -> None:
        self.full_name = self.full_name.strip()
        self.phone = self.phone.strip()
        self.email = self.email.strip().lower()
        self.name_key = normalize_trainee_name(self.full_name)
        self.phone_key = normalize_trainee_phone(self.phone)


class CourseEnrollment(models.Model):
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="trainee_enrollments",
        verbose_name=_("course"),
    )
    trainee = models.ForeignKey(
        Trainee,
        on_delete=models.PROTECT,
        related_name="course_enrollments",
    )
    trainee_number = models.PositiveIntegerField(
        _("trainee number"), validators=[MinValueValidator(1)]
    )
    identity_key = models.CharField(max_length=340, editable=False)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_enrollments",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_enrollments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedTraineeQuerySet.as_manager()

    class Meta:
        ordering = ("course_id", "trainee_number")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("course", "trainee_number"),
                name="trainees_course_number_unique",
            ),
            models.UniqueConstraint(
                fields=("course", "identity_key"),
                name="trainees_course_identity_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(trainee_number__gt=0),
                name="trainees_number_positive",
            ),
            models.CheckConstraint(
                condition=~models.Q(identity_key=""),
                name="trainees_identity_key_not_blank",
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
                name="trainees_enrollment_archive_valid",
            ),
        ]
        permissions = (
            ("archive_enrollment", "Can archive trainee enrollments"),
            ("restore_enrollment", "Can restore trainee enrollments"),
            ("view_all_enrollments", "Can view all trainee enrollments"),
            ("view_managed_enrollments", "Can view managed trainee enrollments"),
            ("view_roster_enrollments", "Can view limited course rosters"),
        )

    def __str__(self) -> str:
        return f"{self.course.code}:{self.trainee_number}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.identity_key = trainee_identity_key(
            self.trainee.full_name, self.trainee.phone
        )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Enrollments cannot be hard-deleted.")


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "preview", _("Preview")
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="trainee_imports",
    )
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.PREVIEW
    )
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField(default=0)
    valid_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="trainee_imports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="confirmed_trainee_imports",
        blank=True,
        null=True,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedTraineeQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (
            ("import_trainees", "Can preview trainee imports"),
            ("confirm_trainee_import", "Can confirm trainee imports"),
            ("view_import_history", "Can view trainee import history"),
        )
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(status__in=("preview", "confirmed", "cancelled")),
                name="trainees_import_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="confirmed",
                        confirmed_by__isnull=False,
                        confirmed_at__isnull=False,
                    )
                    | models.Q(
                        status__in=("preview", "cancelled"),
                        confirmed_by__isnull=True,
                        confirmed_at__isnull=True,
                    )
                ),
                name="trainees_import_confirmation_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code}:{self.original_name}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Import history cannot be deleted.")


class ImportRow(models.Model):
    class Classification(models.TextChoices):
        VALID = "valid", _("Valid")
        WARNING = "warning", _("Warning")
        DUPLICATE = "duplicate", _("Duplicate")
        ERROR = "error", _("Error")

    class Resolution(models.TextChoices):
        CREATE = "create", _("Create")
        SKIP = "skip", _("Skip")
        UPDATE = "update", _("Update")

    batch = models.ForeignKey(
        ImportBatch, on_delete=models.PROTECT, related_name="rows"
    )
    row_number = models.PositiveIntegerField()
    full_name = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.CharField(max_length=254, blank=True)
    identity_key = models.CharField(max_length=340, blank=True)
    classification = models.CharField(
        max_length=16, choices=Classification.choices, db_index=True
    )
    resolution = models.CharField(max_length=16, choices=Resolution.choices, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    duplicate_enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.PROTECT,
        related_name="duplicate_import_rows",
        blank=True,
        null=True,
    )
    created_enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.PROTECT,
        related_name="source_import_rows",
        blank=True,
        null=True,
    )

    objects = ProtectedTraineeQuerySet.as_manager()

    class Meta:
        ordering = ("row_number",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("batch", "row_number"),
                name="trainees_import_row_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    classification__in=("valid", "warning", "duplicate", "error")
                ),
                name="trainees_import_row_class_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(resolution__in=("", "create", "skip", "update")),
                name="trainees_import_row_resolution_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.batch_id}:{self.row_number}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Import rows cannot be deleted.")
