"""Protected request, nonce, and alert records for the CEO Telegram bot."""

from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProtectedExecutiveBotQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Executive bot records cannot be hard-deleted.")


class ExecutiveReportRequest(models.Model):
    class ReportType(models.TextChoices):
        CURRENT_TASKS = "current_tasks", _("Current tasks")
        OVERDUE_TASKS = "overdue_tasks", _("Overdue tasks")
        ATTENDANCE = "attendance", _("Trainee attendance")

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    report_type = models.CharField(max_length=24, choices=ReportType.choices)
    window_days = models.PositiveSmallIntegerField(
        choices=((7, _("7 days")), (14, _("14 days")), (30, _("30 days")))
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="executive_report_requests",
    )
    chat_id_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    output_data = models.JSONField(default=dict, blank=True)
    provider_code = models.CharField(max_length=24, blank=True)
    model_code = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=32, blank=True)
    source_count = models.PositiveSmallIntegerField(default=0)
    source_truncated = models.BooleanField(default=False)
    input_tokens = models.PositiveIntegerField(blank=True, null=True)
    cached_input_tokens = models.PositiveIntegerField(blank=True, null=True)
    output_tokens = models.PositiveIntegerField(blank=True, null=True)
    failure_code = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    downloaded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedExecutiveBotQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        permissions = (
            ("request_executivereport", "Can request CEO Telegram reports"),
            ("receive_critical_alert", "Can receive CEO critical task alerts"),
        )
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("requested_by", "-created_at"),
                name="exec_report_user_created_idx",
            ),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    report_type__in=("current_tasks", "overdue_tasks", "attendance")
                ),
                name="exec_report_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(window_days__in=(7, 14, 30)),
                name="exec_report_window_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("queued", "processing", "completed", "failed")
                ),
                name="exec_report_status_valid",
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
                name="exec_report_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(downloaded_at__isnull=True)
                    | models.Q(status="completed", downloaded_at__isnull=False)
                ),
                name="exec_report_download_state_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.report_type}:{self.pk}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Executive report requests cannot be hard-deleted.")


class CriticalTaskAlert(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        LEASED = "leased", _("Leased")
        DELIVERED = "delivered", _("Delivered")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.PROTECT,
        related_name="critical_telegram_alerts",
    )
    fingerprint = models.CharField(max_length=64, unique=True)
    message_ar = models.CharField(max_length=1000)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    lease_digest = models.CharField(max_length=64, blank=True)
    lease_expires_at = models.DateTimeField(blank=True, null=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedExecutiveBotQuerySet.as_manager()

    class Meta:
        ordering = ("created_at",)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("status", "lease_expires_at"),
                name="critical_alert_lease_idx",
            )
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(status__in=("pending", "leased", "delivered")),
                name="critical_alert_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="pending",
                        lease_digest="",
                        lease_expires_at__isnull=True,
                        delivered_at__isnull=True,
                    )
                    | models.Q(
                        status="leased",
                        lease_digest__gt="",
                        lease_expires_at__isnull=False,
                        delivered_at__isnull=True,
                    )
                    | models.Q(
                        status="delivered",
                        lease_digest="",
                        lease_expires_at__isnull=True,
                        delivered_at__isnull=False,
                    )
                ),
                name="critical_alert_lifecycle_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.status}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Critical task alerts cannot be hard-deleted.")


class N8nRequestNonce(models.Model):
    """Temporary hash-only replay evidence; expired rows may be removed."""

    digest = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("expires_at",)

    def __str__(self) -> str:
        return f"nonce:{self.created_at.isoformat()}"
