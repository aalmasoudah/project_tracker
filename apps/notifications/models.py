"""Protected notification, preference, and delivery records."""

from typing import Any, ClassVar
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.policies import MESSAGE_CATEGORIES


class ProtectedNotificationQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Notification records cannot be hard-deleted.")


class Notification(models.Model):
    class Category(models.TextChoices):
        TASK_ASSIGNMENT = "task_assignment", _("Task assignments")
        APPROVAL = "approval", _("Approvals")
        DEADLINE = "deadline", _("Deadlines and overdue")
        MENTION = "mention", _("Mentions")
        AI_BRIEFING = "ai_briefing", _("AI project briefings")
        PROJECT_AGENT = "project_agent", _("Project recovery agent")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    category = models.CharField(
        _("category"), max_length=24, choices=Category.choices, db_index=True
    )
    message_code = models.CharField(max_length=32)
    event_key = models.CharField(max_length=200)
    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200)
    body_ar = models.TextField()
    body_en = models.TextField()
    target_path = models.CharField(max_length=500, blank=True)
    show_in_app = models.BooleanField(default=True)
    is_read = models.BooleanField(_("read"), default=False, db_index=True)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ProtectedNotificationQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("recipient", "event_key"),
                name="notifications_recipient_event_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    category__in=(
                        "task_assignment",
                        "approval",
                        "deadline",
                        "mention",
                        "ai_briefing",
                        "project_agent",
                    )
                ),
                name="notifications_category_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_read=False, read_at__isnull=True)
                    | models.Q(is_read=True, read_at__isnull=False)
                ),
                name="notifications_read_state_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_id}:{self.event_key}"

    def clean(self) -> None:
        super().clean()
        expected_category = MESSAGE_CATEGORIES.get(self.message_code)
        if expected_category != self.category:
            raise ValidationError(
                {"message_code": _("Select a valid notification message.")}
            )
        if self.target_path:
            parsed = urlsplit(self.target_path)
            unsafe = (
                not self.target_path.startswith("/")
                or self.target_path.startswith("//")
                or bool(parsed.scheme)
                or bool(parsed.netloc)
                or "\\" in self.target_path
                or any(ord(character) < 32 for character in self.target_path)
            )
            if unsafe:
                raise ValidationError(
                    {
                        "target_path": _(
                            "Notification links must stay inside the application."
                        )
                    }
                )

    def localized_title(self, language_code: str) -> str:
        return self.title_ar if language_code == "ar" else self.title_en

    def localized_body(self, language_code: str) -> str:
        return self.body_ar if language_code == "ar" else self.body_en

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Notifications cannot be hard-deleted.")


class NotificationPreference(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notification_preferences",
    )
    category = models.CharField(
        _("category"), max_length=24, choices=Notification.Category.choices
    )
    in_app_enabled = models.BooleanField(_("In-app notifications"), default=True)
    email_enabled = models.BooleanField(_("Email notifications"), default=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedNotificationQuerySet.as_manager()

    class Meta:
        ordering = ("category",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("recipient", "category"),
                name="notifications_preference_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    category__in=(
                        "task_assignment",
                        "approval",
                        "deadline",
                        "mention",
                        "ai_briefing",
                        "project_agent",
                    )
                ),
                name="notifications_preference_category_valid",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(category__in=("approval", "project_agent"))
                    | models.Q(in_app_enabled=True)
                ),
                name="notifications_approval_in_app_required",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_id}:{self.category}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Notification preferences cannot be deleted.")


class DeliveryAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        RETRY = "retry", _("Retry scheduled")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    notification = models.OneToOneField(
        Notification,
        on_delete=models.PROTECT,
        related_name="delivery",
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProtectedNotificationQuerySet.as_manager()

    class Meta:
        ordering = ("next_attempt_at", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("pending", "processing", "retry", "sent", "failed")
                ),
                name="notifications_delivery_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="sent", sent_at__isnull=False)
                    | (~models.Q(status="sent") & models.Q(sent_at__isnull=True))
                ),
                name="notifications_delivery_sent_state_valid",
            ),
        ]
        permissions = (
            ("view_delivery_status", "Can view notification delivery status"),
        )

    def __str__(self) -> str:
        return f"{self.notification_id}:{self.status}"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Delivery records cannot be hard-deleted.")
