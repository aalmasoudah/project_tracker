"""Stable internal role codes and localized presentation labels."""

from dataclasses import dataclass

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

TECHNICAL_ADMIN = "technical_admin"
CEO = "ceo"
EXECUTIVE_MANAGER = "executive_manager"
PROJECT_MANAGER = "project_manager"
SUPERVISOR = "supervisor"
EMPLOYEE = "employee"
CONTRACTOR = "contractor"


@dataclass(frozen=True)
class RoleDefinition:
    """A stable database code with a translated user-facing label."""

    code: str
    label: Promise


ROLE_DEFINITIONS = (
    RoleDefinition(TECHNICAL_ADMIN, _("Technical Admin")),
    RoleDefinition(CEO, _("CEO")),
    RoleDefinition(EXECUTIVE_MANAGER, _("Executive Manager")),
    RoleDefinition(PROJECT_MANAGER, _("Project Manager")),
    RoleDefinition(SUPERVISOR, _("Supervisor")),
    RoleDefinition(EMPLOYEE, _("Employee")),
    RoleDefinition(CONTRACTOR, _("Contractor")),
)

ROLE_CODES = tuple(role.code for role in ROLE_DEFINITIONS)
NON_TECHNICAL_ROLE_CODES = tuple(code for code in ROLE_CODES if code != TECHNICAL_ADMIN)
ROLE_LABELS = {role.code: role.label for role in ROLE_DEFINITIONS}


def role_label(role_code: str | None) -> Promise | str:
    """Return the localized role label without exposing the stable code."""
    if role_code is None:
        return _("No assigned role")
    return ROLE_LABELS.get(role_code, _("Unknown role"))
