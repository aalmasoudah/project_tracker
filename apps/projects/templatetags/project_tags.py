"""Localized project presentation helpers."""

from django import template
from django.utils import translation

from apps.projects.models import ArchivedReference, Project

register = template.Library()


@register.filter
def localized_project_name(project: Project) -> str:
    return project.localized_name(translation.get_language() or "ar")


@register.filter
def localized_reference_name(reference: ArchivedReference | None) -> str:
    if reference is None:
        return "—"
    return reference.localized_name(translation.get_language() or "ar")
