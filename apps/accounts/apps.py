"""Accounts application configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """Configure the custom-user application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = _("Accounts")

    def ready(self) -> None:
        """Register account integrity checks."""
        from apps.accounts import signals  # noqa: F401
