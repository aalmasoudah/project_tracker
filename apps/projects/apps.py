"""Projects application configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    """Configure projects and team membership."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    verbose_name = _("Projects")
