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
    actions.PROJECT_CREATED: _("Project created"),
    actions.PROJECT_UPDATED: _("Project updated"),
    actions.PROJECT_STATUS_CHANGED: _("Project status changed"),
    actions.PROJECT_ARCHIVED: _("Project archived"),
    actions.PROJECT_RESTORED: _("Project restored"),
    actions.PROJECT_TEAM_UPDATED: _("Project team updated"),
    actions.CLIENT_CREATED: _("Client created"),
    actions.CLIENT_UPDATED: _("Client updated"),
    actions.CLIENT_ARCHIVED: _("Client archived"),
    actions.CLIENT_RESTORED: _("Client restored"),
    actions.CATEGORY_CREATED: _("Category created"),
    actions.CATEGORY_UPDATED: _("Category updated"),
    actions.CATEGORY_ARCHIVED: _("Category archived"),
    actions.CATEGORY_RESTORED: _("Category restored"),
}


@register.filter
def audit_action_label(action_code: str) -> object:
    """Translate a stable action code, retaining an unknown safe code."""
    return ACTION_LABELS.get(action_code, action_code)
