from django import template

from apps.notifications.models import Notification

register = template.Library()


@register.filter
def notification_title(notification: Notification, language_code: str) -> str:
    return notification.localized_title(language_code)


@register.filter
def notification_body(notification: Notification, language_code: str) -> str:
    return notification.localized_body(language_code)
