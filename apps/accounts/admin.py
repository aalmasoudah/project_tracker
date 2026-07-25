"""Restricted Django admin support for bootstrap users."""

from typing import TYPE_CHECKING

from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

if TYPE_CHECKING:

    class UserAdminBase(UserAdmin[User]):
        """Typed UserAdmin base used by static analysis."""

else:
    UserAdminBase = UserAdmin


@admin.register(User)
class CustomUserAdmin(UserAdminBase):
    """Keep Django admin as a superuser recovery surface, not the account UI."""

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Approved profile"),
            {
                "fields": (
                    "display_name",
                    "email",
                    "department",
                    "preferred_language",
                    "must_change_password",
                )
            },
        ),
        (
            _("Recovery permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = (
        "username",
        "last_login",
        "date_joined",
    )
    list_display = (
        "username",
        "display_name",
        "email",
        "is_active",
        "is_superuser",
    )
    search_fields = ("username", "display_name", "email")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Require the application workflow for all non-superuser creation."""
        del request
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> bool:
        """Accounts are never hard-deleted."""
        del request, obj
        return False


try:
    admin.site.unregister(Group)
except NotRegistered:
    pass
