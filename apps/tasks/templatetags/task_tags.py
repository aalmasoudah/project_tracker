"""Localized task and tag presentation."""

from django import template
from django.utils.translation import get_language

from apps.tasks.models import Tag, Task

register = template.Library()


@register.filter
def localized_task_name(task: Task) -> str:
    return task.localized_name(get_language() or "ar")


@register.filter
def localized_tag_name(tag: Tag) -> str:
    return tag.localized_name(get_language() or "ar")
