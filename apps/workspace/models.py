"""Private, validated saved filters for Phase 12 operational views."""

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class SavedFilter(models.Model):
    """A versioned filter owned and visible only by one user."""

    class ViewType(models.TextChoices):
        SEARCH = "search", _("Global search")
        KANBAN = "kanban", _("Kanban")
        CALENDAR = "calendar", _("Calendar")
        TIMELINE = "timeline", _("Timeline")
        GANTT = "gantt", _("Gantt")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
    )
    name = models.CharField(_("name"), max_length=100)
    view_type = models.CharField(
        _("view"),
        max_length=16,
        choices=ViewType.choices,
        db_index=True,
    )
    criteria = models.JSONField(_("criteria"), default=dict)
    schema_version = models.PositiveSmallIntegerField(default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("view_type", "name", "pk")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                "owner",
                "view_type",
                Lower("name"),
                name="workspace_filter_owner_view_name_ci_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(schema_version=1),
                name="workspace_filter_schema_v1",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    view_type__in=("search", "kanban", "calendar", "timeline", "gantt")
                ),
                name="workspace_filter_view_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.owner_id}:{self.view_type}:{self.name}"
