"""Permission anchor for stateless report generation."""

from django.db import models


class ReportAccess(models.Model):
    """Unmanaged model that owns explicit Phase 13 export permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("export_project_progress", "Can export project progress reports"),
            ("export_overdue_tasks", "Can export overdue task reports"),
            ("export_course_attendance", "Can export course attendance reports"),
            (
                "export_project_attendance",
                "Can export project attendance reports",
            ),
        )

    def __str__(self) -> str:
        return "Report access"
