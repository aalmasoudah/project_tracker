from typing import Any

from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def localized_name(item: Any) -> str:
    localizer = getattr(item, "localized_name", None)
    if callable(localizer):
        return str(localizer(get_language() or "ar"))
    return str(item)
