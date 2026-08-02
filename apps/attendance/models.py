"""Sessions, hash-only capability links, and reviewed attendance records."""

from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProtectedAttendanceQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Attendance records cannot be hard-deleted.")


class ImmutableAttendanceQuerySet[ModelT: models.Model](
    ProtectedAttendanceQuerySet[ModelT]
):
    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise PermissionDenied("Attendance history is immutable.")


class Session(models.Model):
    class Recurrence(models.TextChoices):
        NONE = "none", _("Does not repeat")
        DAILY = "daily", _("Daily")
        WEEKLY = "weekly", _("Weekly")

    course = models.ForeignKey(
        "courses.Course", on_delete=models.PROTECT, related_name="sessions"
    )
    trainer = models.ForeignKey(
        "courses.Trainer", on_delete=models.PROTECT, related_name="sessions"
    )
    title_ar = models.CharField(_("Arabic title"), max_length=200)
    title_en = models.CharField(_("English title"), max_length=200)
    start_at = models.DateTimeField(_("starts at"), db_index=True)
    end_at = models.DateTimeField(_("ends at"))
    notes = models.TextField(_("notes"), blank=True)
    recurrence_source = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="generated_sessions",
        blank=True,
        null=True,
    )
    occurrence_index = models.PositiveIntegerField(default=1)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_sessions",
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_sessions",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("start_at", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="attendance_session_schedule_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(occurrence_index__gt=0),
                name="attendance_occurrence_positive",
            ),
            models.UniqueConstraint(
                fields=("recurrence_source", "occurrence_index"),
                condition=models.Q(recurrence_source__isnull=False),
                name="attendance_recurrence_occurrence_unique",
            ),
            models.UniqueConstraint(
                fields=("course", "trainer", "start_at"),
                name="attendance_session_start_unique",
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
                name="attendance_session_archive_valid",
            ),
        ]
        permissions = (
            ("manage_all_sessions", "Can manage all sessions"),
            ("manage_managed_sessions", "Can manage sessions in managed courses"),
            ("view_context_sessions", "Can view active context sessions"),
            ("archive_session", "Can archive sessions"),
            ("issue_trainer_link", "Can issue trainer links"),
        )

    def __str__(self) -> str:
        return f"{self.course.code}:{self.start_at.isoformat()}"

    def localized_title(self, language_code: str) -> str:
        return self.title_ar if language_code == "ar" else self.title_en

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Sessions cannot be hard-deleted.")


class SessionParticipant(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.PROTECT, related_name="participants"
    )
    enrollment = models.ForeignKey(
        "trainees.CourseEnrollment",
        on_delete=models.PROTECT,
        related_name="session_participations",
    )

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("enrollment__trainee_number",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("session", "enrollment"),
                name="attendance_session_participant_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_id}:{self.enrollment_id}"


class TrainerLink(models.Model):
    class State(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUBMITTED = "submitted", _("Submitted")
        REVOKED = "revoked", _("Revoked")

    session = models.ForeignKey(
        Session, on_delete=models.PROTECT, related_name="trainer_links"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    state = models.CharField(
        _("state"), max_length=16, choices=State.choices, default=State.ACTIVE
    )
    expires_at = models.DateTimeField(_("expires at"), db_index=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_trainer_links",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("-issued_at", "-pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(state__in=("active", "submitted", "revoked")),
                name="attendance_link_state_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session_id}:{self.state}"


class AttendanceSubmission(models.Model):
    class State(models.TextChoices):
        PENDING_REVIEW = "pending_review", _("Pending supervisor review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    session = models.OneToOneField(
        Session, on_delete=models.PROTECT, related_name="attendance_submission"
    )
    trainer_link = models.OneToOneField(
        TrainerLink, on_delete=models.PROTECT, related_name="submission"
    )
    state = models.CharField(
        _("state"),
        max_length=24,
        choices=State.choices,
        default=State.PENDING_REVIEW,
        db_index=True,
    )
    trainer_notes = models.TextField(_("trainer notes"), blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("-submitted_at",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    state__in=("pending_review", "approved", "rejected")
                ),
                name="attendance_submission_state_valid",
            )
        ]
        permissions = (
            ("review_attendance", "Can review supervised attendance"),
            ("view_all_attendance", "Can view all attendance"),
            ("view_managed_attendance", "Can view managed attendance"),
            ("view_supervised_attendance", "Can view supervised attendance"),
            ("correct_all_attendance", "Can correct all attendance"),
            ("correct_managed_attendance", "Can correct managed attendance"),
        )

    def __str__(self) -> str:
        return f"{self.session_id}:{self.state}"


class AttendanceEntry(models.Model):
    class Value(models.TextChoices):
        PRESENT = "present", _("Present")
        ABSENT = "absent", _("Absent")
        LATE = "late", _("Late")
        EXCUSED = "excused", _("Excused")

    submission = models.ForeignKey(
        AttendanceSubmission, on_delete=models.PROTECT, related_name="entries"
    )
    participant = models.ForeignKey(
        SessionParticipant, on_delete=models.PROTECT, related_name="attendance_entries"
    )
    value = models.CharField(_("attendance"), max_length=16, choices=Value.choices)
    notes = models.CharField(_("notes"), max_length=500, blank=True)

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("participant__enrollment__trainee_number",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("submission", "participant"),
                name="attendance_submission_participant_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(value__in=("present", "absent", "late", "excused")),
                name="attendance_entry_value_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.submission_id}:{self.participant_id}"


def evidence_upload_path(instance: "AttendanceEvidence", filename: str) -> str:
    return (
        f"attendance/{instance.submission.session_id}/"
        f"{uuid4().hex}{Path(filename).suffix.lower()}"
    )


class AttendanceEvidence(models.Model):
    submission = models.ForeignKey(
        AttendanceSubmission, on_delete=models.PROTECT, related_name="evidence"
    )
    file = models.FileField(upload_to=evidence_upload_path, max_length=300)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=150)
    sha256 = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("uploaded_at", "pk")

    def __str__(self) -> str:
        return self.original_name


class ImmutableAttendanceRecord(models.Model):
    """Prevent normal mutation of review and correction evidence."""

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise PermissionDenied("Attendance history is immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Attendance history cannot be deleted.")


class AttendanceReview(ImmutableAttendanceRecord):
    class Decision(models.TextChoices):
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    submission = models.ForeignKey(
        AttendanceSubmission, on_delete=models.PROTECT, related_name="reviews"
    )
    attempt = models.PositiveIntegerField()
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_reviews",
    )
    decision = models.CharField(_("decision"), max_length=16, choices=Decision.choices)
    reason = models.CharField(_("reason"), max_length=1000, blank=True)
    entry_snapshot = models.JSONField(default=list)
    trainer_notes_snapshot = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ImmutableAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("attempt", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("submission", "attempt"),
                name="attendance_review_attempt_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(decision__in=("approved", "rejected")),
                name="attendance_review_decision_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(decision="approved", reason="")
                    | (models.Q(decision="rejected") & ~models.Q(reason=""))
                ),
                name="attendance_review_reason_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.submission_id}:{self.attempt}:{self.decision}"


class AttendanceCorrection(ImmutableAttendanceRecord):
    submission = models.ForeignKey(
        AttendanceSubmission, on_delete=models.PROTECT, related_name="corrections"
    )
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_corrections",
    )
    reason = models.CharField(_("correction reason"), max_length=1000)
    before_snapshot = models.JSONField(default=list)
    after_snapshot = models.JSONField(default=list)
    corrected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ImmutableAttendanceQuerySet.as_manager()

    class Meta:
        ordering = ("corrected_at", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=~models.Q(reason=""),
                name="attendance_correction_reason_required",
            )
        ]

    def __str__(self) -> str:
        return f"{self.submission_id}:{self.pk}"
