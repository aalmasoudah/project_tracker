"""Signed JSON endpoints for safe reviewed-run n8n processing."""

from collections.abc import Callable
from functools import wraps
from typing import cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.project_agents.integration_auth import (
    AuthenticatedN8nRequest,
    IntegrationAuthenticationError,
    authenticate_n8n,
)
from apps.project_agents.integration_services import (
    acknowledge_reviewed_event,
    claim_reviewed_event,
)

JsonView = Callable[[HttpRequest, AuthenticatedN8nRequest], JsonResponse]


def _json(value: dict[str, object], *, status: int = 200) -> JsonResponse:
    response = JsonResponse(
        value, status=status, json_dumps_params={"ensure_ascii": False}
    )
    response["Cache-Control"] = "no-store"
    return response


def signed_view(view: JsonView) -> Callable[[HttpRequest], JsonResponse]:
    @wraps(view)
    def wrapper(request: HttpRequest) -> JsonResponse:
        try:
            return view(request, authenticate_n8n(request))
        except IntegrationAuthenticationError:
            return _json({"error": "unauthorized"}, status=401)
        except PermissionDenied:
            return _json({"error": "not_found"}, status=404)
        except ValidationError:
            return _json({"error": "invalid_request"}, status=400)

    return wrapper


@csrf_exempt
@require_POST
@signed_view
def claim_event(
    request: HttpRequest, authenticated: AuthenticatedN8nRequest
) -> JsonResponse:
    del request
    if authenticated.payload != {}:
        raise ValidationError("Invalid integration payload.")
    return _json(claim_reviewed_event())


@csrf_exempt
@require_POST
@signed_view
def callback(
    request: HttpRequest, authenticated: AuthenticatedN8nRequest
) -> JsonResponse:
    del request
    payload = authenticated.payload
    if set(payload) != {"event_id", "lease_token", "outcome"}:
        raise ValidationError("Invalid integration payload.")
    event_id = payload["event_id"]
    lease_token = payload["lease_token"]
    outcome = payload["outcome"]
    if not all(isinstance(item, str) for item in (event_id, lease_token, outcome)):
        raise ValidationError("Invalid integration payload.")
    event = acknowledge_reviewed_event(
        event_id=cast(str, event_id),
        lease_token=cast(str, lease_token),
        outcome=cast(str, outcome),
    )
    return _json({"event_id": str(event.pk), "status": event.status})
