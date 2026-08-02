"""Owner-scoped notification and operational delivery reads."""

from django.db.models import QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification


def notifications_for(actor: User) -> QuerySet[Notification]:
    return Notification.objects.filter(
        recipient=actor,
        show_in_app=True,
    ).select_related("recipient")


def visible_notification_or_404(actor: User, notification_id: int) -> Notification:
    try:
        return notifications_for(actor).get(pk=notification_id)
    except Notification.DoesNotExist as error:
        raise Http404 from error


def delivery_attempts_for(actor: User) -> QuerySet[DeliveryAttempt]:
    if not actor.has_perm("notifications.view_delivery_status"):
        return DeliveryAttempt.objects.none()
    return DeliveryAttempt.objects.select_related("notification__recipient").order_by(
        "-updated_at", "-pk"
    )
