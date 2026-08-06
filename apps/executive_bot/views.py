"""Narrow JSON/PDF endpoints authenticated by the approved n8n signature."""

from collections.abc import Callable
from functools import wraps
from typing import cast

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.executive_bot.assistant_validation import detect_question_language
from apps.executive_bot.authentication import (
    AuthenticatedIntegrationRequest,
    IntegrationAuthenticationError,
    authenticate_signed_request,
)
from apps.executive_bot.services import (
    acknowledge_critical_alerts,
    assistant_status_payload,
    claim_critical_alerts,
    consume_report_download,
    latest_completed_assistant_request,
    report_status_payload,
    request_assistant_answer,
    request_report,
    visible_assistant_request,
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
            "kind": "report",
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


def _rejected_question_payload(
    *, question: object, failure_code: str
) -> dict[str, object]:
    language = detect_question_language(question) if isinstance(question, str) else "ar"
    if language == "ar":
        if failure_code == "daily_limit":
            message = "تم الوصول إلى الحد اليومي لأسئلة المساعد. حاول غداً."
        else:
            message = (
                "يمكنني الإجابة فقط عن مخاطر المشاريع والمهام والمواعيد "
                "والتعطل والتقدم والاعتمادات. لا أستطيع تنفيذ تغييرات أو "
                "الوصول إلى الأسرار أو البيانات الشخصية."
            )
    elif failure_code == "daily_limit":
        message = "The daily assistant question limit has been reached. Try tomorrow."
    else:
        message = (
            "I can only answer about project/task risks, deadlines, blockers, "
            "progress, and approvals. I cannot change records or access secrets "
            "or personal data."
        )
    return {
        "kind": "assistant",
        "status": "rejected",
        "failure_code": failure_code,
        "language": language,
        "message": message,
    }


@csrf_exempt
@require_POST
@signed_json_view
def start_assistant(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    payload = _exact_payload(
        authenticated.payload,
        {"chat_id", "message_id", "question"},
    )
    chat_id = payload["chat_id"]
    message_id = payload["message_id"]
    question = payload["question"]
    if not isinstance(chat_id, str) or not isinstance(message_id, str):
        raise ValidationError("invalid_request")
    try:
        assistant_request, created = request_assistant_answer(
            actor=authenticated.actor,
            chat_id=chat_id,
            message_id=message_id,
            question=question,
            request=request,
        )
    except ValidationError as error:
        failure_code = str(error.messages[0]) if error.messages else "invalid_question"
        return _json(
            _rejected_question_payload(
                question=question,
                failure_code=failure_code,
            )
        )
    return _json(
        {
            "kind": "assistant",
            "request_id": str(assistant_request.pk),
            "status": assistant_request.status,
            "language": assistant_request.language,
            "created": created,
            "message": (
                "تم استلام السؤال وجارٍ تحليل الأدلة الحالية."
                if assistant_request.language == "ar"
                else "The question was received and current evidence is being analyzed."
            ),
        },
        status=202 if created else 200,
    )


@csrf_exempt
@require_POST
@signed_json_view
def assistant_status(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    del request
    payload = _exact_payload(authenticated.payload, {"chat_id", "request_id"})
    chat_id = payload["chat_id"]
    request_id = payload["request_id"]
    if not isinstance(chat_id, str) or not isinstance(request_id, str):
        raise ValidationError("invalid_request")
    assistant_request = visible_assistant_request(
        actor=authenticated.actor,
        chat_id=chat_id,
        request_id=request_id,
    )
    return _json(assistant_status_payload(assistant_request))


@csrf_exempt
@require_POST
@signed_json_view
def assistant_latest(
    request: HttpRequest,
    authenticated: AuthenticatedIntegrationRequest,
) -> JsonResponse:
    del request
    payload = _exact_payload(authenticated.payload, {"chat_id"})
    chat_id = payload["chat_id"]
    if not isinstance(chat_id, str):
        raise ValidationError("invalid_request")
    assistant_request = latest_completed_assistant_request(
        actor=authenticated.actor,
        chat_id=chat_id,
    )
    return _json(assistant_status_payload(assistant_request))


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
