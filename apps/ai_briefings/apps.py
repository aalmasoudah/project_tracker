from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AIBriefingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_briefings"
    verbose_name = _("AI project briefings")
