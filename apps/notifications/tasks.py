"""Idempotent Celery delivery and scheduled reminder tasks."""

from datetime import timedelta

# Celery does not publish PEP 561 type metadata.
from celery import Task, shared_task  # type: ignore[import-untyped]
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.notifications.emailing import send_notification_email
from apps.notifications.events import generate_task_deadline_notifications
from apps.notifications.models import DeliveryAttempt
from apps.notifications.policies import (
    DELIVERY_RETRY_SECONDS,
    MAX_DELIVERY_ATTEMPTS,
)


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    max_retries=MAX_DELIVERY_ATTEMPTS - 1,
)
def deliver_notification_email(self: Task, delivery_id: int) -> str:
    now = timezone.now()
    with transaction.atomic():
        delivery = (
            DeliveryAttempt.objects.select_for_update()
            .select_related("notification__recipient")
            .get(pk=delivery_id)
        )
        if delivery.status in (
            DeliveryAttempt.Status.SENT,
            DeliveryAttempt.Status.FAILED,
        ):
            return delivery.status
        if delivery.status == DeliveryAttempt.Status.PROCESSING:
            return delivery.status
        if delivery.next_attempt_at > now:
            return delivery.status
        delivery.status = DeliveryAttempt.Status.PROCESSING
        delivery.attempts += 1
        delivery.last_attempt_at = now
        delivery.last_error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "attempts",
                "last_attempt_at",
                "last_error_code",
                "updated_at",
            )
        )
        notification = delivery.notification
    try:
        sent_count = send_notification_email(notification)
        if sent_count != 1:
            raise RuntimeError("Email backend did not confirm one delivery.")
    except Exception as error:
        with transaction.atomic():
            delivery = DeliveryAttempt.objects.select_for_update().get(pk=delivery_id)
            exhausted = delivery.attempts >= MAX_DELIVERY_ATTEMPTS
            retry_index = min(
                max(delivery.attempts - 1, 0),
                len(DELIVERY_RETRY_SECONDS) - 1,
            )
            retry_seconds = DELIVERY_RETRY_SECONDS[retry_index]
            delivery.status = (
                DeliveryAttempt.Status.FAILED
                if exhausted
                else DeliveryAttempt.Status.RETRY
            )
            delivery.next_attempt_at = timezone.now() + timedelta(seconds=retry_seconds)
            delivery.last_error_code = type(error).__name__[:64]
            delivery.save(
                update_fields=(
                    "status",
                    "next_attempt_at",
                    "last_error_code",
                    "updated_at",
                )
            )
        if not exhausted:
            raise self.retry(
                exc=RuntimeError("Notification email delivery failed."),
                countdown=retry_seconds,
            ) from error
        return DeliveryAttempt.Status.FAILED
    with transaction.atomic():
        delivery = DeliveryAttempt.objects.select_for_update().get(pk=delivery_id)
        delivery.status = DeliveryAttempt.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.last_error_code = ""
        delivery.save(
            update_fields=(
                "status",
                "sent_at",
                "last_error_code",
                "updated_at",
            )
        )
    return DeliveryAttempt.Status.SENT


@shared_task  # type: ignore[untyped-decorator]
def dispatch_pending_deliveries() -> int:
    stale_before = timezone.now() - timedelta(minutes=15)
    DeliveryAttempt.objects.filter(
        status=DeliveryAttempt.Status.PROCESSING,
    ).filter(
        Q(last_attempt_at__lt=stale_before) | Q(last_attempt_at__isnull=True)
    ).update(
        status=DeliveryAttempt.Status.RETRY,
        next_attempt_at=timezone.now(),
        last_error_code="WorkerInterrupted",
    )
    delivery_ids = list(
        DeliveryAttempt.objects.filter(
            status__in=(
                DeliveryAttempt.Status.PENDING,
                DeliveryAttempt.Status.RETRY,
            ),
            next_attempt_at__lte=timezone.now(),
        )
        .order_by("next_attempt_at", "pk")
        .values_list("pk", flat=True)[:100]
    )
    for delivery_id in delivery_ids:
        deliver_notification_email.delay(delivery_id)
    return len(delivery_ids)


@shared_task  # type: ignore[untyped-decorator]
def generate_task_reminders() -> int:
    return generate_task_deadline_notifications()
