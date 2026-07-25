"""Restricted Django admin support for bootstrap users."""

from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User

if TYPE_CHECKING:

    class UserAdminBase(UserAdmin[User]):
        """Typed UserAdmin base used by static analysis."""

else:
    UserAdminBase = UserAdmin


@admin.register(User)
class CustomUserAdmin(UserAdminBase):
    """Use Django's hardened user administration for the custom model."""
