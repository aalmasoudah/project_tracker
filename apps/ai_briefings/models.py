"""Protected request, result, and evidence-reference records."""

from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProtectedBriefingQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    """Reject normal hard deletion under the indefinite retention rule."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("AI briefing records cannot be hard-deleted.")


class AIBriefing(models.Model):
    """One immutable-input AI briefing request and its validated output."""

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    class Language(models.TextChoices):
        ARABIC = "ar", _("Arabic")
        ENGLISH = "en", _("English")

    class DetailLevel(models.TextChoices):
        EXECUTIVE = "executive", _("Executive detail")
        OPERATIONAL = "operational", _("Operational detail")

    class EvidenceWindow(models.IntegerChoices):
        SEVEN_DAYS = 7, _("7 days")
        FOURTEEN_DAYS = 14, _("14 days")
        THIRTY_DAYS = 30, _("30 days")

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="ai_briefings",
        verbose_name=_("project"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_ai_briefings",
        verbose_name=_("requested by"),
    )
    language = models.CharField(
        _("language"),
        max_length=2,
        choices=Language.choices,
    )
    detail_level = models.CharField(
        _("detail level"),
        max_length=16,
        choices=DetailLevel.choices,
    )
    evidence_window_days = models.PositiveSmallIntegerField(
        _("evidence window"),
        choices=EvidenceWindow.choices,
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    output_data = models.JSONField(default=dict, blank=True)
    provider_code = models.CharField(max_length=24, blank=True)
    model_code = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=32, blank=True)
    input_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    evidence_count = models.PositiveSmallIntegerField(default=0)
    evidence_truncated = models.BooleanField(default=False)
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    cached_input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)
    failure_code = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_ai_briefings",
        blank=True,
        null=True,
        verbose_name=_("reviewed by"),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedBriefingQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "-pk")
        permissions = (
            ("generate_aibriefing", "Can generate AI project briefings"),
            ("review_aibriefing", "Can review AI project briefings"),
        )
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(language__in=("ar", "en")),
                name="ai_briefings_language_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(detail_level__in=("executive", "operational")),
                name="ai_briefings_detail_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(evidence_window_days__in=(7, 14, 30)),
                name="ai_briefings_window_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("queued", "processing", "completed", "failed")
                ),
                name="ai_briefings_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="queued",
                        started_at__isnull=True,
                        completed_at__isnull=True,
                    )
                    | models.Q(
                        status="processing",
                        started_at__isnull=False,
                        completed_at__isnull=True,
                    )
                    | models.Q(
                        status__in=("completed", "failed"),
                        started_at__isnull=False,
                        completed_at__isnull=False,
                    )
                ),
                name="ai_briefings_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(reviewed_at__isnull=True, reviewed_by__isnull=True)
                    | models.Q(reviewed_at__isnull=False, reviewed_by__isnull=False)
                ),
                name="ai_briefings_review_state_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("project", "-created_at"),
                name="ai_brief_project_created_idx",
            ),
            models.Index(
                fields=("requested_by", "-created_at"),
                name="ai_brief_user_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.code}:{self.pk}:{self.status}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("AI briefings cannot be hard-deleted.")


class AIBriefingSource(models.Model):
    """An allowlisted internal source cited by one completed briefing."""

    class SourceType(models.TextChoices):
        PROJECT = "project", _("Project")
        TASK = "task", _("Task")
        MILESTONE = "milestone", _("Milestone")
        APPROVAL = "approval", _("Approval")
        AUDIT = "audit", _("Audit event")

    briefing = models.ForeignKey(
        AIBriefing,
        on_delete=models.PROTECT,
        related_name="sources",
    )
    source_ref = models.CharField(max_length=100)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    source_id = models.CharField(max_length=64)
    source_label = models.CharField(max_length=250)
    source_updated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ProtectedBriefingQuerySet.as_manager()

    class Meta:
        ordering = ("source_type", "source_id")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("briefing", "source_ref"),
                name="ai_briefings_source_ref_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    source_type__in=(
                        "project",
                        "task",
                        "milestone",
                        "approval",
                        "audit",
                    )
                ),
                name="ai_briefings_source_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.briefing_id}:{self.source_ref}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("AI briefing sources cannot be hard-deleted.")
