"""Permission-scoped audit query helpers."""

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.audit.models import AuditEvent


def audit_events_visible_to(actor: User) -> QuerySet[AuditEvent]:
    """Return security-scope events only to approved Technical Admin actors."""
    if not actor.has_perm("audit.view_auditevent"):
        raise PermissionDenied("Audit visibility permission is required.")
    return AuditEvent.objects.select_related("actor").filter(
        scope=AuditEvent.Scope.SECURITY
    )
