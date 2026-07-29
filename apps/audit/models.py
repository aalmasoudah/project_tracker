"""Append-only security and lifecycle audit records."""

from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class AppendOnlyAuditQuerySet(models.QuerySet["AuditEvent"]):
    """Reject bulk mutation and deletion of audit history."""

    def update(self, **kwargs: Any) -> int:
        del kwargs
        raise PermissionDenied("Audit events are append-only.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Audit events cannot be deleted.")


class AuditEvent(models.Model):
    """A safe append-only record of a security-relevant event."""

    class Scope(models.TextChoices):
        SECURITY = "security", _("Security")
        PROJECTS = "projects", _("Projects")
        COURSES = "courses", _("Courses")
        TASKS = "tasks", _("Tasks")
        APPROVALS = "approvals", _("Approvals")
        TRAINEES = "trainees", _("Trainees")
        ATTENDANCE = "attendance", _("Attendance")
        NOTIFICATIONS = "notifications", _("Notifications")

    scope = models.CharField(
        _("scope"),
        max_length=32,
        choices=Scope.choices,
        default=Scope.SECURITY,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
        blank=True,
        null=True,
        verbose_name=_("actor"),
    )
    action = models.CharField(_("action"), max_length=64, db_index=True)
    target_type = models.CharField(_("target type"), max_length=64)
    target_id = models.CharField(_("target ID"), max_length=64, blank=True)
    target_label = models.CharField(_("target label"), max_length=200, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict)
    correlation_id = models.CharField(
        _("correlation ID"),
        max_length=64,
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    objects = AppendOnlyAuditQuerySet.as_manager()

    class Meta:
        default_permissions = ("view",)
        ordering = ("-created_at", "-pk")
        verbose_name = _("audit event")
        verbose_name_plural = _("audit events")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("target_type", "target_id"),
                name="audit_target_lookup_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.target_type}:{self.target_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Allow creation but reject later mutation."""
        if not self._state.adding:
            raise PermissionDenied("Audit events are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Reject audit deletion through normal application paths."""
        del args, kwargs
        raise PermissionDenied("Audit events cannot be deleted.")
