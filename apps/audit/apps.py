"""Audit application configuration."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configure security-relevant append-only audit events."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"
