"""Narrow JSON/PDF endpoints authenticated by the approved n8n signature."""

from collections.abc import Callable
from functools import wraps
from typing import cast

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.executive_bot.authentication import (
    AuthenticatedIntegrationRequest,
    IntegrationAuthenticationError,
    authenticate_signed_request,
)
from apps.executive_bot.services import (
    acknowledge_critical_alerts,
    claim_critical_alerts,
    consume_report_download,
    report_status_payload,
    request_report,
    visible_report,
)

JsonView = Callable[[HttpRequest, AuthenticatedIntegrationRequest], JsonResponse]


def _json(payload: dict[str, object], *, status: int = 200) -> JsonResponse:
    response = JsonResponse(
        payload,
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )
    response["Cache-Control"] = "no-store"
    return response


def signed_json_view(view: JsonView) -> Callable[[HttpRequest], JsonResponse]:
    @wraps(view)
    def wrapper(request: HttpRequest) -> JsonResponse:
        try:
            authenticated = authenticate_signed_request(request)
            return view(request, authenticated)
        except IntegrationAuthenticationError:
            return _json({"error": "unauthorized"}, status=401)
        except (PermissionDenied, Http404):
            return _json({"error": "not_found"}, status=404)
        except ValidationError:
            return _json({"error": "invalid_request"}, status=400)

    return wrapper


def _exact_payload(payload: dict[str, object], expected: set[str]) -> dict[str, object]:
    if set(payload) != expected:
        raise ValidationError("Invalid integration payload.")
    return payload


@csrf_exempt
@require_POST
@signed_json_view
def start_report(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    payload = _exact_payload(
        authenticated.payload,
        {"chat_id", "report_type", "window_days"},
    )
    chat_id = payload["chat_id"]
    report_type = payload["report_type"]
    window_days = payload["window_days"]
    if (
        not isinstance(chat_id, str)
        or not isinstance(report_type, str)
        or isinstance(window_days, bool)
        or not isinstance(window_days, int)
    ):
        raise ValidationError("Invalid integration payload.")
    report = request_report(
        actor=authenticated.actor,
        chat_id=chat_id,
        report_type=report_type,
        window_days=window_days,
        request=request,
    )
    return _json(
        {
            "request_id": str(report.pk),
            "status": report.status,
            "message_ar": "تم استلام الطلب وجارٍ إعداد التقرير.",
        },
        status=202,
    )


@csrf_exempt
@require_POST
@signed_json_view
def report_status(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    del request
    payload = _exact_payload(authenticated.payload, {"chat_id", "request_id"})
    chat_id = payload["chat_id"]
    report_id = payload["request_id"]
    if not isinstance(chat_id, str) or not isinstance(report_id, str):
        raise ValidationError("Invalid integration payload.")
    report = visible_report(
        actor=authenticated.actor,
        chat_id=chat_id,
        report_id=report_id,
    )
    return _json(report_status_payload(report))


@csrf_exempt
@require_POST
@signed_json_view
def claim_alerts(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    del request
    payload = _exact_payload(authenticated.payload, {"chat_id"})
    chat_id = payload["chat_id"]
    if not isinstance(chat_id, str):
        raise ValidationError("Invalid integration payload.")
    lease_token, alerts = claim_critical_alerts(
        actor=authenticated.actor,
        chat_id=chat_id,
    )
    return _json(
        {
            "lease_token": lease_token,
            "alerts": cast(list[object], alerts),
        }
    )


@csrf_exempt
@require_POST
@signed_json_view
def acknowledge_alerts(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    del request
    payload = _exact_payload(
        authenticated.payload,
        {"chat_id", "lease_token", "alert_ids"},
    )
    chat_id = payload["chat_id"]
    lease_token = payload["lease_token"]
    alert_ids = payload["alert_ids"]
    if (
        not isinstance(chat_id, str)
        or not isinstance(lease_token, str)
        or not isinstance(alert_ids, list)
        or any(not isinstance(item, str) for item in alert_ids)
    ):
        raise ValidationError("Invalid integration payload.")
    delivered = acknowledge_critical_alerts(
        actor=authenticated.actor,
        chat_id=chat_id,
        lease_token=lease_token,
        alert_ids=cast(list[str], alert_ids),
    )
    return _json({"delivered": delivered})


@require_GET
def download_report(request: HttpRequest, report_id: str) -> HttpResponse:
    if not bool(settings.EXECUTIVE_BOT_ENABLED):
        raise Http404
    token = request.GET.get("token", "")
    if not token or len(token) > 2048:
        raise Http404
    content, filename = consume_report_download(report_id=str(report_id), token=token)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
