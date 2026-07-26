"""Safe creation helpers for append-only audit records."""

import ipaddress
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from django.http import HttpRequest

from apps.audit.models import AuditEvent

if TYPE_CHECKING:
    from apps.accounts.models import User

SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|session|authorization|cookie)",
    re.IGNORECASE,
)
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def client_ip_address(request: HttpRequest | None) -> str | None:
    """Return a validated direct peer address without trusting proxy headers."""
    if request is None:
        return None
    candidate = request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def request_correlation_id(request: HttpRequest | None) -> str:
    """Reuse a safe request ID or create a correlation-friendly identifier."""
    if request is not None:
        candidate = request.headers.get("X-Request-ID", "")
        if CORRELATION_ID_PATTERN.fullmatch(candidate):
            return candidate
        existing = str(request.META.get("insight.audit_correlation_id", ""))
        if CORRELATION_ID_PATTERN.fullmatch(existing):
            return existing

    correlation_id = str(uuid4())
    if request is not None:
        request.META["insight.audit_correlation_id"] = correlation_id
    return correlation_id


def _sanitize_metadata(value: Any) -> Any:
    """Remove sensitive keys and coerce values into safe JSON-compatible data."""
    if isinstance(value, Mapping):
        return {
            str(key): _sanitize_metadata(item)
            for key, item in value.items()
            if not SENSITIVE_KEY_PATTERN.search(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_metadata(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def record_audit_event(
    *,
    action: str,
    target_type: str,
    actor: "User | None" = None,
    target_id: str = "",
    target_label: str = "",
    metadata: Mapping[str, Any] | None = None,
    request: HttpRequest | None = None,
    scope: str = AuditEvent.Scope.SECURITY,
) -> AuditEvent:
    """Create one sanitized append-only audit event."""
    return AuditEvent.objects.create(
        scope=scope,
        actor=actor if actor is not None and actor.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label[:200],
        metadata=_sanitize_metadata(metadata or {}),
        correlation_id=request_correlation_id(request),
        ip_address=client_ip_address(request),
    )
