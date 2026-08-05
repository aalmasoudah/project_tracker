from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectAgentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.project_agents"
    verbose_name = _("Project recovery agent")
