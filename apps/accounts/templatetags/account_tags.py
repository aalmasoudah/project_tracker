"""Localized account and department presentation helpers."""

from django import template
from django.utils.translation import get_language

from apps.accounts.models import User
from apps.accounts.roles import role_label
from apps.accounts.services import managed_role_code
from apps.organizations.models import Department

register = template.Library()


@register.filter
def user_role_label(user: User) -> object:
    """Return a translated role label without exposing the group code."""
    return role_label(managed_role_code(user))


@register.filter
def department_name(department: Department | None) -> str:
    """Return the current-language department name."""
    if department is None:
        return "—"
    return department.localized_name(get_language() or "ar")
