"""HMAC and replay protection for the optional Phase 17 n8n boundary."""

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

from apps.project_agents.models import AgentIntegrationNonce

NONCE_PATTERN: Final = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class IntegrationAuthenticationError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedN8nRequest:
    payload: dict[str, object]


def canonical_request(
    *, timestamp: str, nonce: str, method: str, path: str, body: bytes
) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return "\n".join((timestamp, nonce, method.upper(), path, digest)).encode("utf-8")


def request_signature(
    *, secret: str, timestamp: str, nonce: str, method: str, path: str, body: bytes
) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_request(
            timestamp=timestamp, nonce=nonce, method=method, path=path, body=body
        ),
        hashlib.sha256,
    ).hexdigest()


def event_signature(*, secret: str, payload: dict[str, object]) -> str:
    body = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def authenticate_n8n(request: HttpRequest) -> AuthenticatedN8nRequest:
    if not bool(settings.PROJECT_AGENT_N8N_ENABLED):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    if request.content_type != "application/json" or len(request.body) > 8_192:
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    timestamp = request.headers.get("X-Insight-Timestamp", "")
    nonce = request.headers.get("X-Insight-Nonce", "")
    supplied = request.headers.get("X-Insight-Signature", "").lower()
    secret = str(settings.PROJECT_AGENT_N8N_SIGNING_SECRET)
    if len(secret.encode("utf-8")) < 32 or not NONCE_PATTERN.fullmatch(nonce):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    try:
        epoch = int(timestamp)
    except ValueError as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    if abs(int(time.time()) - epoch) > int(
        settings.PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS
    ):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    expected = request_signature(
        secret=secret,
        timestamp=timestamp,
        nonce=nonce,
        method=request.method or "",
        path=request.path,
        body=request.body,
    )
    if not hmac.compare_digest(supplied, expected):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError) as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    if not isinstance(payload, dict):
        raise IntegrationAuthenticationError("Unauthorized integration request.")
    try:
        with transaction.atomic():
            AgentIntegrationNonce.objects.create(
                nonce_hash=hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
                expires_at=timezone.now()
                + timedelta(
                    seconds=int(settings.PROJECT_AGENT_N8N_SIGNATURE_TTL_SECONDS)
                ),
            )
    except IntegrityError as error:
        raise IntegrationAuthenticationError(
            "Unauthorized integration request."
        ) from error
    return AuthenticatedN8nRequest(payload=payload)


def cleanup_expired_nonces() -> int:
    deleted, _details = AgentIntegrationNonce.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    return deleted
