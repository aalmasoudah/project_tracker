from django import template

from apps.approvals.models import Milestone

register = template.Library()


@register.filter
def localized_milestone_name(milestone: Milestone, language_code: str) -> str:
    return milestone.localized_name(language_code)
