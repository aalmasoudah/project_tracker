"""Localized labels for stable audit action codes."""

from django import template
from django.utils import timezone
from django.utils.translation import get_language

from apps.audit.models import AuditEvent
from apps.audit.presentation import action_label, target_type_label
from apps.reports.dates import format_dual_date

register = template.Library()


@register.filter
def audit_action_label(action_code: str) -> object:
    """Translate a stable action code, retaining an unknown safe code."""
    return action_label(action_code)


@register.filter
def audit_target_type_label(target_type: str) -> object:
    return target_type_label(target_type)


@register.filter
def audit_scope_label(scope: str) -> object:
    try:
        return AuditEvent.Scope(scope).label
    except ValueError:
        return scope


@register.filter
def dual_datetime(value: object) -> str:
    if not hasattr(value, "date"):
        return ""
    localized = timezone.localtime(value)  # type: ignore[arg-type]
    language_code = (get_language() or "ar")[:2]
    return f"{format_dual_date(localized.date(), language_code)} {localized:%H:%M}"
