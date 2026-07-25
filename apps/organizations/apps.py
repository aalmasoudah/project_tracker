"""Organization application configuration."""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """Configure departments and organization membership."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organizations"
    verbose_name = "Organizations"
