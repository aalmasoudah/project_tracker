"""Small authenticated unread-notification summary."""

from typing import Any

from django.http import HttpRequest

from apps.notifications.models import Notification


def notification_summary(request: HttpRequest) -> dict[str, Any]:
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}
    return {
        "unread_notification_count": Notification.objects.filter(
            recipient=request.user,
            show_in_app=True,
            is_read=False,
        ).count()
    }
