"""Permission-scoped Phase 14 audit query helpers."""

from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.policies import (
    BUSINESS_AUDIT_SCOPES,
    SAFE_METADATA_KEYS,
    SECURITY_AUDIT_SCOPES,
)


def permitted_audit_scopes(actor: User) -> tuple[str, ...]:
    """Return stable scopes the actor may access without role-name checks."""
    scopes: set[str] = set()
    if actor.has_perm("audit.view_security_audit"):
        scopes.update(SECURITY_AUDIT_SCOPES)
    if actor.has_perm("audit.view_business_audit"):
        scopes.update(BUSINESS_AUDIT_SCOPES)
    return tuple(scope for scope in AuditEvent.Scope.values if scope in scopes)


def audit_events_visible_to(
    actor: User,
    *,
    scope: str = "",
    action: str = "",
    target_type: str = "",
    query: str = "",
    correlation_id: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[AuditEvent]:
    """Return only approved audit scopes with allowlisted filters."""
    scopes = permitted_audit_scopes(actor)
    if not scopes:
        raise PermissionDenied("Audit visibility permission is required.")
    if scope:
        if scope not in scopes:
            raise PermissionDenied("This audit scope is not available.")
        scopes = (scope,)
    events = AuditEvent.objects.select_related("actor").filter(scope__in=scopes)
    if action:
        events = events.filter(action=action)
    if target_type:
        events = events.filter(target_type=target_type)
    if query:
        events = events.filter(
            Q(target_label__icontains=query)
            | Q(target_id__icontains=query)
            | Q(actor__display_name__icontains=query)
            | Q(actor__username__icontains=query)
        )
    if correlation_id:
        events = events.filter(correlation_id=correlation_id)
    current_timezone = timezone.get_current_timezone()
    if date_from is not None:
        lower = timezone.make_aware(
            datetime.combine(date_from, time.min),
            current_timezone,
        )
        events = events.filter(created_at__gte=lower)
    if date_to is not None:
        upper = timezone.make_aware(
            datetime.combine(date_to + timedelta(days=1), time.min),
            current_timezone,
        )
        events = events.filter(created_at__lt=upper)
    return events


def visible_audit_event_or_404(actor: User, event_id: int) -> AuditEvent:
    try:
        return audit_events_visible_to(actor).get(pk=event_id)
    except AuditEvent.DoesNotExist as error:
        raise Http404 from error


def can_export_audit(actor: User, scopes: tuple[str, ...]) -> bool:
    """Require the matching export permission for every requested scope."""
    requested = set(scopes)
    if requested & SECURITY_AUDIT_SCOPES and not actor.has_perm(
        "audit.export_security_audit"
    ):
        return False
    if requested & BUSINESS_AUDIT_SCOPES and not actor.has_perm(
        "audit.export_business_audit"
    ):
        return False
    return bool(requested)


def _safe_metadata_value(value: Any) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:500]
    if isinstance(value, (list, tuple)):
        return [_safe_metadata_value(item) for item in value[:50]]
    if isinstance(value, dict):
        return {
            str(key)[:64]: _safe_metadata_value(item)
            for key, item in list(value.items())[:50]
        }
    return str(value)[:500]


def safe_audit_metadata(event: AuditEvent) -> dict[str, object]:
    """Return only explicitly approved metadata keys for presentation."""
    return {
        key: _safe_metadata_value(event.metadata[key])
        for key in sorted(event.metadata)
        if key in SAFE_METADATA_KEYS
    }
