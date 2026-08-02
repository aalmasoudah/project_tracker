"""Permission anchor for non-persistent Phase 14 operational views."""

from django.db import models


class OperationsAccess(models.Model):
    """Unmanaged owner of explicit operations permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("view_operations_status", "Can view safe operations status"),
            ("view_archive_center", "Can view the archive center"),
        )

    def __str__(self) -> str:
        return "Operations access"
