"""Lease-based reviewed-event handoff to the optional n8n workflow."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.project_agents.integration_auth import event_signature
from apps.project_agents.models import AgentReviewedEvent


@transaction.atomic
def claim_reviewed_event() -> dict[str, object]:
    now = timezone.now()
    event = (
        AgentReviewedEvent.objects.select_for_update(skip_locked=True)
        .filter(
            status__in=(
                AgentReviewedEvent.Status.PENDING,
                AgentReviewedEvent.Status.LEASED,
            )
        )
        .filter(
            models.Q(status=AgentReviewedEvent.Status.PENDING)
            | models.Q(status=AgentReviewedEvent.Status.LEASED, leased_until__lt=now)
        )
        .order_by("created_at")
        .first()
    )
    if event is None:
        return {"event": None}
    token = secrets.token_urlsafe(32)
    event.status = AgentReviewedEvent.Status.LEASED
    event.lease_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    event.leased_until = now + timedelta(minutes=5)
    event.save(
        update_fields=("status", "lease_token_hash", "leased_until", "updated_at")
    )
    payload = event.safe_payload if isinstance(event.safe_payload, dict) else {}
    return {
        "event_id": str(event.pk),
        "lease_token": token,
        "payload": payload,
        "event_signature": event_signature(
            secret=str(settings.PROJECT_AGENT_N8N_SIGNING_SECRET), payload=payload
        ),
    }


@transaction.atomic
def acknowledge_reviewed_event(
    *, event_id: str, lease_token: str, outcome: str
) -> AgentReviewedEvent:
    if outcome not in {"notified", "archived", "rejected", "failed"}:
        raise ValidationError("Invalid reviewed-event outcome.")
    try:
        event = AgentReviewedEvent.objects.select_for_update().get(pk=event_id)
    except (AgentReviewedEvent.DoesNotExist, ValueError) as error:
        raise PermissionDenied("Reviewed event is not available.") from error
    if event.status in (
        AgentReviewedEvent.Status.ACKNOWLEDGED,
        AgentReviewedEvent.Status.FAILED,
    ):
        if hmac.compare_digest(event.callback_code, outcome):
            return event
        raise PermissionDenied("Reviewed event is not available.")
    if (
        event.status != AgentReviewedEvent.Status.LEASED
        or event.leased_until is None
        or event.leased_until < timezone.now()
        or not hmac.compare_digest(
            event.lease_token_hash,
            hashlib.sha256(lease_token.encode("utf-8")).hexdigest(),
        )
    ):
        raise PermissionDenied("Reviewed event is not available.")
    event.status = (
        AgentReviewedEvent.Status.FAILED
        if outcome == "failed"
        else AgentReviewedEvent.Status.ACKNOWLEDGED
    )
    event.callback_code = outcome
    event.acknowledged_at = timezone.now()
    event.lease_token_hash = ""
    event.leased_until = None
    event.save(
        update_fields=(
            "status",
            "callback_code",
            "acknowledged_at",
            "lease_token_hash",
            "leased_until",
            "updated_at",
        )
    )
    return event
