"""Replay-resistant authentication for the narrow n8n integration API."""

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import User
from apps.executive_bot.models import N8nRequestNonce

NONCE_PATTERN: Final = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class IntegrationAuthenticationError(PermissionError):
    """Safe authentication failure without caller-specific detail."""


@dataclass(frozen=True, slots=True)
class AuthenticatedIntegrationRequest:
    actor: User
    payload: dict[str, object]


def canonical_request(
    *,
    timestamp: str,
    nonce: str,
    method: str,
    path: str,
    body: bytes,
) -> bytes:
    body_digest = hashlib.sha256(body).hexdigest()
    return "\n".join((timestamp, nonce, method.upper(), path, body_digest)).encode(
        "utf-8"
    )


def request_signature(
    *,
    secret: str,
    timestamp: str,
    nonce: str,
    method: str,
    path: str,
    body: bytes,
) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_request(
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            path=path,
            body=body,
        ),
        hashlib.sha256,
    ).hexdigest()


def _consume_nonce(nonce: str) -> None:
    now = timezone.now()
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    expires_at = now + timedelta(
        seconds=int(settings.EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS)
    )
    try:
        with transaction.atomic():
            N8nRequestNonce.objects.create(digest=digest, expires_at=expires_at)
    except IntegrityError as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error


def cleanup_expired_nonces() -> int:
    deleted, _details = N8nRequestNonce.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    return deleted


def _configured_ceo() -> User:
    username = str(settings.EXECUTIVE_BOT_CEO_USERNAME).strip()
    try:
        actor = User.objects.get(username__iexact=username, is_active=True)
    except (User.DoesNotExist, User.MultipleObjectsReturned) as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    if not actor.groups.filter(name="ceo").exists():
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    if not actor.has_perm("executive_bot.request_executivereport"):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    return actor


def authenticate_signed_request(
    request: HttpRequest,
) -> AuthenticatedIntegrationRequest:
    if not bool(settings.EXECUTIVE_BOT_ENABLED):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    content_length = request.META.get("CONTENT_LENGTH", "")
    try:
        declared_length = int(content_length) if content_length else 0
    except ValueError as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    max_body_bytes = int(settings.EXECUTIVE_BOT_MAX_BODY_BYTES)
    if declared_length < 0 or declared_length > max_body_bytes:
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    if request.content_type != "application/json":
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    body = request.body
    if len(body) > max_body_bytes:
        raise IntegrationAuthenticationError("Unauthorized integration request.")

    timestamp = request.headers.get("X-Insight-Timestamp", "")
    nonce = request.headers.get("X-Insight-Nonce", "")
    supplied_signature = request.headers.get("X-Insight-Signature", "").lower()
    secret = str(settings.EXECUTIVE_BOT_SIGNING_SECRET)
    if not secret or not NONCE_PATTERN.fullmatch(nonce):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    try:
        request_epoch = int(timestamp)
    except ValueError as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    if abs(int(time.time()) - request_epoch) > int(
        settings.EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS
    ):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    expected_signature = request_signature(
        secret=secret,
        timestamp=timestamp,
        nonce=nonce,
        method=request.method or "",
        path=request.path,
        body=body,
    )
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    try:
        payload = json.loads(body)
    except (TypeError, ValueError) as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    if not isinstance(payload, dict):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    chat_id = payload.get("chat_id")
    configured_chat_id = str(settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID).strip()
    if not isinstance(chat_id, str) or not hmac.compare_digest(
        chat_id.encode("utf-8"), configured_chat_id.encode("utf-8")
    ):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    _consume_nonce(nonce)
    return AuthenticatedIntegrationRequest(actor=_configured_ceo(), payload=payload)
