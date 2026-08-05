from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExecutiveBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.executive_bot"
    verbose_name = _("CEO Telegram reports")
