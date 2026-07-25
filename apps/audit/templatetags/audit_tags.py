"""Localized labels for stable audit action codes."""

from django import template
from django.utils.translation import gettext_lazy as _

from apps.audit import actions

register = template.Library()

ACTION_LABELS = {
    actions.LOGIN_SUCCEEDED: _("Login succeeded"),
    actions.LOGIN_FAILED: _("Login failed"),
    actions.LOGIN_LOCKED: _("Login temporarily locked"),
    actions.LOGOUT: _("Logout"),
    actions.PASSWORD_CHANGED: _("Password changed"),
    actions.PASSWORD_RESET: _("Password reset"),
    actions.ACCOUNT_CREATED: _("Account created"),
    actions.ACCOUNT_UPDATED: _("Account updated"),
    actions.ACCOUNT_DEACTIVATED: _("Account deactivated"),
    actions.ACCOUNT_REACTIVATED: _("Account reactivated"),
    actions.LANGUAGE_CHANGED: _("Language preference changed"),
    actions.DEPARTMENT_CREATED: _("Department created"),
    actions.DEPARTMENT_UPDATED: _("Department updated"),
    actions.DEPARTMENT_ARCHIVED: _("Department archived"),
    actions.DEPARTMENT_RESTORED: _("Department restored"),
}


@register.filter
def audit_action_label(action_code: str) -> object:
    """Translate a stable action code, retaining an unknown safe code."""
    return ACTION_LABELS.get(action_code, action_code)
