"""Authentication models created before all later business domains."""

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user identity reserved for approved later account behavior."""

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
