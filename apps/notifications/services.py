"""Transactional notification creation, preferences, and read-state services."""

import logging
from collections.abc import Mapping
from functools import partial

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    NotificationPreference,
)
from apps.notifications.policies import (
    CATEGORY_POLICIES,
    MESSAGE_CATEGORIES,
    MESSAGE_CONTENT,
)

logger = logging.getLogger(__name__)


def preference_values(recipient: User) -> dict[str, tuple[bool, bool]]:
    stored = {
        preference.category: preference
        for preference in NotificationPreference.objects.filter(recipient=recipient)
    }
    values: dict[str, tuple[bool, bool]] = {}
    for category, policy in CATEGORY_POLICIES.items():
        preference = stored.get(category)
        in_app = (
            preference.in_app_enabled
            if preference is not None
            else policy.default_in_app
        )
        email = (
            preference.email_enabled if preference is not None else policy.default_email
        )
        values[category] = (in_app or policy.mandatory_in_app, email)
    return values


def _queue_delivery(delivery_id: int) -> None:
    try:
        from apps.notifications.tasks import deliver_notification_email

        deliver_notification_email.delay(delivery_id)
    except Exception:
        logger.exception(
            "Notification delivery enqueue failed.",
            extra={"delivery_id": delivery_id},
        )


def _has_deliverable_email(recipient: User) -> bool:
    if not recipient.email:
        return False
    try:
        validate_email(recipient.email)
    except ValidationError:
        logger.warning(
            "Notification email skipped because the account address is invalid.",
            extra={"recipient_id": recipient.pk},
        )
        return False
    return True


@transaction.atomic
def create_notification(
    *,
    recipient: User,
    message_code: str,
    event_key: str,
    target_path: str = "",
) -> Notification | None:
    if not recipient.is_active:
        return None
    content = MESSAGE_CONTENT.get(message_code)
    if content is None:
        raise ValidationError(_("Select a valid notification message."))
    notification_category = MESSAGE_CATEGORIES[message_code]
    in_app_enabled, email_enabled = preference_values(recipient)[notification_category]
    if not in_app_enabled and not email_enabled:
        return None
    candidate = Notification(
        recipient=recipient,
        category=notification_category,
        message_code=message_code,
        event_key=event_key,
        title_ar=content.title_ar,
        title_en=content.title_en,
        body_ar=content.body_ar,
        body_en=content.body_en,
        target_path=target_path,
        show_in_app=in_app_enabled,
    )
    candidate.full_clean(
        exclude=("id",),
        validate_unique=False,
        validate_constraints=False,
    )
    notification, created = Notification.objects.get_or_create(
        recipient=recipient,
        event_key=event_key,
        defaults={
            "category": candidate.category,
            "message_code": candidate.message_code,
            "title_ar": candidate.title_ar,
            "title_en": candidate.title_en,
            "body_ar": candidate.body_ar,
            "body_en": candidate.body_en,
            "target_path": candidate.target_path,
            "show_in_app": candidate.show_in_app,
        },
    )
    if created and email_enabled and _has_deliverable_email(recipient):
        delivery = DeliveryAttempt.objects.create(notification=notification)
        transaction.on_commit(partial(_queue_delivery, delivery.pk))
    return notification if created else None


@transaction.atomic
def update_preferences(
    *,
    actor: User,
    values: Mapping[str, tuple[bool, bool]],
    request: HttpRequest | None = None,
) -> None:
    if not actor.is_active:
        raise PermissionDenied(_("An active account is required."))
    if set(values) != set(CATEGORY_POLICIES):
        raise ValidationError(_("Select valid notification categories."))
    for category, (in_app_enabled, email_enabled) in values.items():
        policy = CATEGORY_POLICIES[category]
        NotificationPreference.objects.update_or_create(
            recipient=actor,
            category=category,
            defaults={
                "in_app_enabled": in_app_enabled or policy.mandatory_in_app,
                "email_enabled": email_enabled,
            },
        )
    record_audit_event(
        actor=actor,
        action=actions.NOTIFICATION_PREFERENCES_UPDATED,
        target_type="notification_preferences",
        target_id=str(actor.pk),
        target_label=actor.username,
        metadata={"categories": sorted(values)},
        request=request,
        scope=AuditEvent.Scope.NOTIFICATIONS,
    )


@transaction.atomic
def mark_notification_read(*, actor: User, notification: Notification) -> Notification:
    try:
        notification = Notification.objects.select_for_update().get(
            pk=notification.pk,
            recipient=actor,
            show_in_app=True,
        )
    except Notification.DoesNotExist as error:
        raise PermissionDenied(_("This notification is not available.")) from error
    if notification.is_read:
        return notification
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=("is_read", "read_at"))
    return notification


@transaction.atomic
def mark_all_notifications_read(*, actor: User) -> int:
    return Notification.objects.filter(
        recipient=actor,
        show_in_app=True,
        is_read=False,
    ).update(is_read=True, read_at=timezone.now())
