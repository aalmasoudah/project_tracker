"""Transactional executive report, download, and critical-alert workflows."""

import hashlib
import logging
import re
import secrets
from datetime import datetime, time, timedelta
from functools import partial
from typing import cast
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.utils import timezone, translation

from apps.accounts.models import User
from apps.ai_briefings.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    TemporaryProviderError,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.executive_bot.assistant_evidence import build_assistant_evidence
from apps.executive_bot.assistant_provider import (
    PROMPT_VERSION as ASSISTANT_PROMPT_VERSION,
)
from apps.executive_bot.assistant_provider import (
    format_assistant_message,
    generate_assistant_answer,
)
from apps.executive_bot.assistant_validation import validate_executive_question
from apps.executive_bot.evidence import (
    ExecutiveEvidence,
    build_executive_evidence,
    critical_tasks_for,
)
from apps.executive_bot.models import (
    CriticalTaskAlert,
    ExecutiveAssistantRequest,
    ExecutiveReportRequest,
)
from apps.executive_bot.policies import (
    can_use_executive_assistant,
    can_use_executive_bot,
    chat_id_hash,
)
from apps.executive_bot.provider import PROMPT_VERSION, generate_executive_summary
from apps.reports.datasets import ReportDocument
from apps.reports.dates import format_dual_date
from apps.reports.renderers import render_pdf
from apps.tasks.models import Task

logger = logging.getLogger(__name__)
DOWNLOAD_SIGNING_SALT = "executive-bot-report-download-v1"


def _queue_report(report_id: str) -> None:
    try:
        from apps.executive_bot.tasks import generate_executive_report

        generate_executive_report.delay(report_id)
    except Exception:
        logger.exception(
            "Executive report enqueue failed.", extra={"report_id": report_id}
        )
        mark_report_failed(report_id=report_id, failure_code="enqueue_failed")


def _queue_assistant(request_id: str) -> None:
    try:
        from apps.executive_bot.tasks import generate_executive_answer

        generate_executive_answer.delay(request_id)
    except Exception:
        logger.exception(
            "Executive assistant enqueue failed.",
            extra={"assistant_request_id": request_id},
        )
        mark_assistant_failed(request_id=request_id, failure_code="enqueue_failed")


def _local_day_bounds() -> tuple[datetime, datetime]:
    local_date = timezone.localdate()
    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(
        datetime.combine(local_date, time.min), current_timezone
    )
    return start, start + timedelta(days=1)


@transaction.atomic
def request_report(
    *,
    actor: User,
    chat_id: str,
    report_type: str,
    window_days: int,
    request: HttpRequest | None = None,
) -> ExecutiveReportRequest:
    if not can_use_executive_bot(actor, chat_id):
        raise PermissionDenied("Executive bot access is required.")
    if report_type not in ExecutiveReportRequest.ReportType.values:
        raise ValidationError("Invalid report type.")
    if window_days not in (7, 14, 30):
        raise ValidationError("Invalid report window.")
    User.objects.select_for_update().get(pk=actor.pk)
    day_start, day_end = _local_day_bounds()
    request_count = ExecutiveReportRequest.objects.filter(
        requested_by=actor,
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).count()
    if request_count >= int(settings.EXECUTIVE_BOT_DAILY_LIMIT):
        raise ValidationError("Daily report request limit reached.")
    report = ExecutiveReportRequest.objects.create(
        report_type=report_type,
        window_days=window_days,
        requested_by=actor,
        chat_id_hash=chat_id_hash(chat_id),
    )
    record_audit_event(
        actor=actor,
        action=actions.EXECUTIVE_REPORT_REQUESTED,
        target_type="executive_report",
        target_id=str(report.pk),
        target_label=report.report_type,
        metadata={
            "report_type": report.report_type,
            "window_days": report.window_days,
            "status": report.status,
        },
        request=request,
        scope=AuditEvent.Scope.EXECUTIVE_BOT,
    )
    transaction.on_commit(partial(_queue_report, str(report.pk)))
    return report


@transaction.atomic
def request_assistant_answer(
    *,
    actor: User,
    chat_id: str,
    message_id: str,
    question: object,
    request: HttpRequest | None = None,
) -> tuple[ExecutiveAssistantRequest, bool]:
    if not can_use_executive_assistant(actor, chat_id):
        raise PermissionDenied("Executive assistant access is required.")
    if not message_id.isascii() or not message_id.isdigit() or len(message_id) > 20:
        raise ValidationError("invalid_message_id")
    cleaned_question, language = validate_executive_question(question)
    message_key_hash = hashlib.sha256(f"{chat_id}:{message_id}".encode()).hexdigest()
    existing = ExecutiveAssistantRequest.objects.filter(
        message_key_hash=message_key_hash
    ).first()
    if existing is not None:
        if existing.requested_by_id != actor.pk or not secrets.compare_digest(
            existing.chat_id_hash, chat_id_hash(chat_id)
        ):
            raise PermissionDenied("Executive assistant access is required.")
        return existing, False

    User.objects.select_for_update().get(pk=actor.pk)
    day_start, day_end = _local_day_bounds()
    request_count = ExecutiveAssistantRequest.objects.filter(
        requested_by=actor,
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).count()
    if request_count >= int(settings.EXECUTIVE_ASSISTANT_DAILY_LIMIT):
        raise ValidationError("daily_limit")
    try:
        with transaction.atomic():
            assistant_request = ExecutiveAssistantRequest.objects.create(
                requested_by=actor,
                chat_id_hash=chat_id_hash(chat_id),
                message_key_hash=message_key_hash,
                question_text=cleaned_question,
                question_hash=hashlib.sha256(cleaned_question.encode()).hexdigest(),
                language=language,
            )
    except IntegrityError:
        concurrent = ExecutiveAssistantRequest.objects.get(
            message_key_hash=message_key_hash
        )
        if concurrent.requested_by_id != actor.pk or not secrets.compare_digest(
            concurrent.chat_id_hash, chat_id_hash(chat_id)
        ):
            raise PermissionDenied("Executive assistant access is required.") from None
        return concurrent, False
    record_audit_event(
        actor=actor,
        action=actions.EXECUTIVE_ASSISTANT_REQUESTED,
        target_type="executive_assistant_request",
        target_id=str(assistant_request.pk),
        target_label="executive_assistant",
        metadata={"language": language, "status": assistant_request.status},
        request=request,
        scope=AuditEvent.Scope.EXECUTIVE_BOT,
    )
    transaction.on_commit(partial(_queue_assistant, str(assistant_request.pk)))
    return assistant_request, True


def _document_data(document: ReportDocument) -> dict[str, object]:
    return {
        "title": document.title,
        "subtitle": document.subtitle,
        "headers": list(document.headers),
        "rows": [list(row) for row in document.rows],
        "filename_stem": document.filename_stem,
        "sheet_name": document.sheet_name,
        "column_weights": list(document.column_weights),
    }


def _complete_report(
    *,
    report: ExecutiveReportRequest,
    evidence: ExecutiveEvidence,
    summary: dict[str, object],
    provider_code: str,
    model_code: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
    fallback_from_provider: str | None = None,
    fallback_reason_code: str | None = None,
) -> str:
    with transaction.atomic():
        locked = ExecutiveReportRequest.objects.select_for_update().get(pk=report.pk)
        if locked.status in (
            ExecutiveReportRequest.Status.COMPLETED,
            ExecutiveReportRequest.Status.FAILED,
        ):
            return locked.status
        locked.status = ExecutiveReportRequest.Status.COMPLETED
        locked.output_data = {
            "document": _document_data(evidence.document),
            "summary": summary,
            "source_labels": evidence.source_labels,
        }
        locked.provider_code = provider_code
        locked.model_code = model_code
        locked.prompt_version = PROMPT_VERSION
        locked.source_count = evidence.source_count
        locked.source_truncated = evidence.truncated
        locked.input_tokens = input_tokens
        locked.cached_input_tokens = cached_input_tokens
        locked.output_tokens = output_tokens
        locked.failure_code = ""
        locked.completed_at = timezone.now()
        locked.save(
            update_fields=(
                "status",
                "output_data",
                "provider_code",
                "model_code",
                "prompt_version",
                "source_count",
                "source_truncated",
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "failure_code",
                "completed_at",
                "updated_at",
            )
        )
        record_audit_event(
            actor=locked.requested_by,
            action=actions.EXECUTIVE_REPORT_COMPLETED,
            target_type="executive_report",
            target_id=str(locked.pk),
            target_label=locked.report_type,
            metadata={
                "report_type": locked.report_type,
                "status": locked.status,
                "source_count": locked.source_count,
                "source_truncated": locked.source_truncated,
                "model_code": locked.model_code,
                "provider_code": locked.provider_code,
                "fallback_from_provider": fallback_from_provider or "",
                "fallback_reason_code": fallback_reason_code or "",
            },
            scope=AuditEvent.Scope.EXECUTIVE_BOT,
        )
    return ExecutiveReportRequest.Status.COMPLETED


def generate_report(*, report_id: str) -> str:
    with transaction.atomic():
        report = (
            ExecutiveReportRequest.objects.select_for_update()
            .select_related("requested_by")
            .get(pk=report_id)
        )
        if report.status in (
            ExecutiveReportRequest.Status.COMPLETED,
            ExecutiveReportRequest.Status.FAILED,
        ):
            return report.status
        if report.status == ExecutiveReportRequest.Status.PROCESSING:
            return report.status
        report.status = ExecutiveReportRequest.Status.PROCESSING
        report.started_at = timezone.now()
        report.save(update_fields=("status", "started_at", "updated_at"))
    try:
        configured_chat = str(settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID).strip()
        if not can_use_executive_bot(report.requested_by, configured_chat):
            raise PermissionDenied("Executive bot access is required.")
        if not secrets.compare_digest(
            report.chat_id_hash,
            chat_id_hash(configured_chat),
        ):
            raise PermissionDenied("Executive bot access is required.")
        with translation.override("ar"):
            evidence = build_executive_evidence(
                actor=report.requested_by,
                report_type=report.report_type,
                window_days=report.window_days,
            )
            summary, provider_result = generate_executive_summary(
                evidence=evidence.provider_payload,
                allowed_citations=evidence.allowed_citations,
            )
    except TemporaryProviderError:
        _requeue_report(report_id=report_id)
        raise
    except PermissionDenied:
        return mark_report_failed(report_id=report_id, failure_code="access_revoked")
    except ProviderConfigurationError:
        return mark_report_failed(
            report_id=report_id,
            failure_code="provider_unavailable",
        )
    except ProviderResponseError:
        return mark_report_failed(
            report_id=report_id,
            failure_code="invalid_provider_response",
        )
    except Exception:
        logger.exception(
            "Executive report generation failed.",
            extra={"report_id": report_id},
        )
        return mark_report_failed(report_id=report_id, failure_code="generation_failed")
    return _complete_report(
        report=report,
        evidence=evidence,
        summary=cast(dict[str, object], summary),
        provider_code=provider_result.provider_code,
        model_code=provider_result.model_code,
        input_tokens=provider_result.input_tokens,
        cached_input_tokens=provider_result.cached_input_tokens,
        output_tokens=provider_result.output_tokens,
        fallback_from_provider=provider_result.fallback_from_provider,
        fallback_reason_code=provider_result.fallback_reason_code,
    )


@transaction.atomic
def _requeue_report(*, report_id: str) -> None:
    report = ExecutiveReportRequest.objects.select_for_update().get(pk=report_id)
    if report.status != ExecutiveReportRequest.Status.PROCESSING:
        return
    report.status = ExecutiveReportRequest.Status.QUEUED
    report.started_at = None
    report.save(update_fields=("status", "started_at", "updated_at"))


@transaction.atomic
def mark_report_failed(*, report_id: str, failure_code: str) -> str:
    report = (
        ExecutiveReportRequest.objects.select_for_update()
        .select_related("requested_by")
        .get(pk=report_id)
    )
    if report.status == ExecutiveReportRequest.Status.COMPLETED:
        return report.status
    if report.status == ExecutiveReportRequest.Status.FAILED:
        return report.status
    now = timezone.now()
    report.status = ExecutiveReportRequest.Status.FAILED
    report.started_at = report.started_at or now
    report.completed_at = now
    report.failure_code = failure_code[:64]
    report.output_data = {}
    report.save(
        update_fields=(
            "status",
            "started_at",
            "completed_at",
            "failure_code",
            "output_data",
            "updated_at",
        )
    )
    record_audit_event(
        actor=report.requested_by,
        action=actions.EXECUTIVE_REPORT_FAILED,
        target_type="executive_report",
        target_id=str(report.pk),
        target_label=report.report_type,
        metadata={
            "report_type": report.report_type,
            "status": report.status,
            "failure_code": report.failure_code,
        },
        scope=AuditEvent.Scope.EXECUTIVE_BOT,
    )
    return report.status


def recover_stale_reports() -> int:
    stale_before = timezone.now() - timedelta(
        minutes=int(settings.EXECUTIVE_BOT_STALE_MINUTES)
    )
    report_ids = list(
        ExecutiveReportRequest.objects.filter(
            status=ExecutiveReportRequest.Status.PROCESSING,
            started_at__lt=stale_before,
        )
        .order_by("started_at")
        .values_list("pk", flat=True)[:100]
    )
    recovered: list[str] = []
    for report_id in report_ids:
        with transaction.atomic():
            report = ExecutiveReportRequest.objects.select_for_update().get(
                pk=report_id
            )
            if (
                report.status != ExecutiveReportRequest.Status.PROCESSING
                or report.started_at is None
                or report.started_at >= stale_before
            ):
                continue
            report.status = ExecutiveReportRequest.Status.QUEUED
            report.started_at = None
            report.save(update_fields=("status", "started_at", "updated_at"))
            recovered.append(str(report.pk))
    for recovered_report_id in recovered:
        _queue_report(recovered_report_id)
    return len(recovered)


def visible_report(
    *, actor: User, chat_id: str, report_id: str
) -> ExecutiveReportRequest:
    if not can_use_executive_bot(actor, chat_id):
        raise Http404
    try:
        return ExecutiveReportRequest.objects.select_related("requested_by").get(
            pk=report_id,
            requested_by=actor,
            chat_id_hash=chat_id_hash(chat_id),
        )
    except (ExecutiveReportRequest.DoesNotExist, ValueError) as error:
        raise Http404 from error


def create_download_path(report: ExecutiveReportRequest) -> str:
    token = signing.dumps(
        {"report_id": str(report.pk), "chat_id_hash": report.chat_id_hash},
        salt=DOWNLOAD_SIGNING_SALT,
        compress=True,
    )
    path = reverse("executive_bot:download", args=(report.pk,))
    return f"{path}?{urlencode({'token': token})}"


def create_download_url(report: ExecutiveReportRequest) -> str:
    return f"{str(settings.APP_BASE_URL).rstrip('/')}{create_download_path(report)}"


def report_status_payload(report: ExecutiveReportRequest) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "report",
        "request_id": str(report.pk),
        "status": report.status,
        "report_type": report.report_type,
    }
    if report.status == ExecutiveReportRequest.Status.COMPLETED:
        summary = report.output_data.get("summary", {})
        summary_text = summary.get("summary", "") if isinstance(summary, dict) else ""
        download_path = create_download_path(report)
        payload.update(
            {
                "message_ar": str(summary_text)[:1500],
                "download_path": download_path,
                "download_url": (
                    f"{str(settings.APP_BASE_URL).rstrip('/')}{download_path}"
                ),
                "download_expires_seconds": int(
                    settings.EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS
                ),
            }
        )
    elif report.status == ExecutiveReportRequest.Status.FAILED:
        payload["message_ar"] = "تعذر إنشاء التقرير. يرجى المحاولة لاحقاً."
    else:
        payload["message_ar"] = "جاري إعداد التقرير التنفيذي."
    return payload


def _summary_sections(
    output_data: dict[str, object],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    summary = output_data.get("summary")
    labels = output_data.get("source_labels")
    if not isinstance(summary, dict) or not isinstance(labels, dict):
        raise ValueError("Stored executive report summary is invalid.")

    severity_labels = {
        "critical": "حرج",
        "high": "عالٍ",
        "medium": "متوسط",
        "low": "منخفض",
    }
    report_term_labels = {
        "todo": "قيد البدء",
        "in_progress": "قيد التنفيذ",
        "blocked": "محجوبة",
        "critical": "حرجة",
        "high": "عالية",
        "medium": "متوسطة",
        "low": "منخفضة",
    }
    report_term_pattern = re.compile(
        rf"(?<![A-Za-z0-9_])({'|'.join(report_term_labels)})(?![A-Za-z0-9_])",
        flags=re.IGNORECASE,
    )
    quoted_report_term_pattern = re.compile(
        rf'["“”]({"|".join(report_term_labels)})["“”]',
        flags=re.IGNORECASE,
    )

    def localized_report_text(value: str) -> str:
        without_code_quotes = quoted_report_term_pattern.sub(
            lambda match: report_term_labels[match.group(1).lower()],
            value,
        )
        return report_term_pattern.sub(
            lambda match: report_term_labels[match.group(1).lower()],
            without_code_quotes,
        )

    def compact_source_label(reference: str) -> str:
        label = str(labels.get(reference, reference))
        return label.split(" - ", 1)[0].strip()

    def cited_lines(key: str, *, include_severity: bool = False) -> tuple[str, ...]:
        value = summary.get(key)
        if not isinstance(value, list):
            return ()
        lines: list[str] = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str):
                continue
            references = item.get("citations", [])
            reference_labels = [
                compact_source_label(reference)
                for reference in references
                if isinstance(reference, str)
            ]
            severity_code = str(item.get("severity", "")).lower()
            severity_label = severity_labels.get(severity_code, severity_code)
            severity = f" (الخطورة: {severity_label})" if include_severity else ""
            citations = (
                f" [المصادر: {'، '.join(reference_labels)}]" if reference_labels else ""
            )
            lines.append(f"{localized_report_text(item['text'])}{severity}{citations}")
        return tuple(lines)

    sections: list[tuple[str, tuple[str, ...]]] = []
    summary_text = summary.get("summary")
    if isinstance(summary_text, str) and summary_text:
        sections.append(("الملخص التنفيذي", (localized_report_text(summary_text),)))
    section_specs = (
        ("أبرز النقاط", "highlights", False),
        ("المخاطر", "risks", True),
        ("العناصر القادمة", "upcoming", False),
        ("الإجراءات المقترحة", "recommended_actions", False),
    )
    for title, key, include_severity in section_specs:
        lines = cited_lines(key, include_severity=include_severity)
        if lines:
            sections.append((title, lines))
    data_gaps = summary.get("data_gaps")
    if isinstance(data_gaps, list):
        gaps = tuple(
            localized_report_text(item) for item in data_gaps if isinstance(item, str)
        )
        if gaps:
            sections.append(("فجوات البيانات", gaps))
    return tuple(sections)


def _stored_document(output_data: dict[str, object]) -> ReportDocument:
    data = output_data.get("document")
    if not isinstance(data, dict):
        raise ValueError("Stored executive report document is invalid.")
    headers = data.get("headers")
    rows = data.get("rows")
    column_weights = data.get("column_weights", [])
    if not isinstance(headers, list) or not isinstance(rows, list):
        raise ValueError("Stored executive report table is invalid.")
    if not isinstance(column_weights, list):
        raise ValueError("Stored executive report column widths are invalid.")
    return ReportDocument(
        title=str(data["title"]),
        subtitle=str(data["subtitle"]),
        headers=tuple(str(item) for item in headers),
        rows=tuple(
            tuple(str(cell) for cell in row) for row in rows if isinstance(row, list)
        ),
        filename_stem=str(data["filename_stem"]),
        sheet_name=str(data["sheet_name"]),
        sections=_summary_sections(output_data),
        column_weights=tuple(float(weight) for weight in column_weights),
    )


def consume_report_download(*, report_id: str, token: str) -> tuple[bytes, str]:
    try:
        signed = signing.loads(
            token,
            salt=DOWNLOAD_SIGNING_SALT,
            max_age=int(settings.EXECUTIVE_BOT_DOWNLOAD_TTL_SECONDS),
        )
    except signing.BadSignature as error:
        raise Http404 from error
    if not isinstance(signed, dict):
        raise Http404
    if not secrets.compare_digest(str(signed.get("report_id", "")), report_id):
        raise Http404
    with transaction.atomic():
        try:
            report = (
                ExecutiveReportRequest.objects.select_for_update()
                .select_related("requested_by")
                .get(pk=report_id)
            )
        except (ExecutiveReportRequest.DoesNotExist, ValueError) as error:
            raise Http404 from error
        if report.status != ExecutiveReportRequest.Status.COMPLETED:
            raise Http404
        if report.downloaded_at is not None:
            raise Http404
        if not secrets.compare_digest(
            str(signed.get("chat_id_hash", "")),
            report.chat_id_hash,
        ):
            raise Http404
        with translation.override("ar"):
            document = _stored_document(cast(dict[str, object], report.output_data))
            content = render_pdf(document, language_code="ar")
        report.downloaded_at = timezone.now()
        report.save(update_fields=("downloaded_at", "updated_at"))
        record_audit_event(
            actor=report.requested_by,
            action=actions.EXECUTIVE_REPORT_DOWNLOADED,
            target_type="executive_report",
            target_id=str(report.pk),
            target_label=report.report_type,
            metadata={"report_type": report.report_type, "status": report.status},
            scope=AuditEvent.Scope.EXECUTIVE_BOT,
        )
    date_suffix = timezone.localdate().isoformat()
    filename = f"insight-tracker-{document.filename_stem}-{date_suffix}.pdf"
    return content, filename


def _complete_assistant_request(
    *,
    assistant_request: ExecutiveAssistantRequest,
    answer: dict[str, object],
    message: str,
    source_labels: dict[str, str],
    source_count: int,
    source_truncated: bool,
    provider_code: str,
    model_code: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
    fallback_from_provider: str | None = None,
    fallback_reason_code: str | None = None,
) -> str:
    with transaction.atomic():
        locked = ExecutiveAssistantRequest.objects.select_for_update().get(
            pk=assistant_request.pk
        )
        if locked.status in (
            ExecutiveAssistantRequest.Status.COMPLETED,
            ExecutiveAssistantRequest.Status.FAILED,
        ):
            return locked.status
        locked.status = ExecutiveAssistantRequest.Status.COMPLETED
        locked.output_data = {
            "answer": answer,
            "message": message,
            "source_labels": source_labels,
        }
        locked.provider_code = provider_code
        locked.model_code = model_code
        locked.prompt_version = ASSISTANT_PROMPT_VERSION
        locked.source_count = source_count
        locked.source_truncated = source_truncated
        locked.input_tokens = input_tokens
        locked.cached_input_tokens = cached_input_tokens
        locked.output_tokens = output_tokens
        locked.failure_code = ""
        locked.completed_at = timezone.now()
        locked.save(
            update_fields=(
                "status",
                "output_data",
                "provider_code",
                "model_code",
                "prompt_version",
                "source_count",
                "source_truncated",
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "failure_code",
                "completed_at",
                "updated_at",
            )
        )
        record_audit_event(
            actor=locked.requested_by,
            action=actions.EXECUTIVE_ASSISTANT_COMPLETED,
            target_type="executive_assistant_request",
            target_id=str(locked.pk),
            target_label="executive_assistant",
            metadata={
                "language": locked.language,
                "status": locked.status,
                "source_count": locked.source_count,
                "source_truncated": locked.source_truncated,
                "model_code": locked.model_code,
                "provider_code": locked.provider_code,
                "fallback_from_provider": fallback_from_provider or "",
                "fallback_reason_code": fallback_reason_code or "",
            },
            scope=AuditEvent.Scope.EXECUTIVE_BOT,
        )
    return ExecutiveAssistantRequest.Status.COMPLETED


def generate_assistant_request(*, request_id: str) -> str:
    with transaction.atomic():
        assistant_request = (
            ExecutiveAssistantRequest.objects.select_for_update()
            .select_related("requested_by")
            .get(pk=request_id)
        )
        if assistant_request.status in (
            ExecutiveAssistantRequest.Status.COMPLETED,
            ExecutiveAssistantRequest.Status.FAILED,
        ):
            return assistant_request.status
        if assistant_request.status == ExecutiveAssistantRequest.Status.PROCESSING:
            return assistant_request.status
        assistant_request.status = ExecutiveAssistantRequest.Status.PROCESSING
        assistant_request.started_at = timezone.now()
        assistant_request.save(update_fields=("status", "started_at", "updated_at"))
    try:
        configured_chat = str(settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID).strip()
        if not can_use_executive_assistant(
            assistant_request.requested_by, configured_chat
        ):
            raise PermissionDenied("Executive assistant access is required.")
        if not secrets.compare_digest(
            assistant_request.chat_id_hash,
            chat_id_hash(configured_chat),
        ):
            raise PermissionDenied("Executive assistant access is required.")
        cleaned, language = validate_executive_question(assistant_request.question_text)
        if language != assistant_request.language or not secrets.compare_digest(
            hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            assistant_request.question_hash,
        ):
            raise PermissionDenied("Executive assistant request changed.")
        evidence = build_assistant_evidence(
            actor=assistant_request.requested_by,
            question=cleaned,
            language=language,
        )
        output, provider_result = generate_assistant_answer(
            evidence=evidence.provider_payload,
            allowed_citations=evidence.allowed_citations,
        )
        message = format_assistant_message(
            output=output,
            source_labels=evidence.source_labels,
            language=language,
        )
    except TemporaryProviderError:
        _requeue_assistant_request(request_id=request_id)
        raise
    except PermissionDenied:
        return mark_assistant_failed(
            request_id=request_id, failure_code="access_revoked"
        )
    except ProviderConfigurationError:
        return mark_assistant_failed(
            request_id=request_id, failure_code="provider_unavailable"
        )
    except ProviderResponseError:
        return mark_assistant_failed(
            request_id=request_id, failure_code="invalid_provider_response"
        )
    except Exception:
        logger.exception(
            "Executive assistant generation failed.",
            extra={"assistant_request_id": request_id},
        )
        return mark_assistant_failed(
            request_id=request_id, failure_code="generation_failed"
        )
    return _complete_assistant_request(
        assistant_request=assistant_request,
        answer=cast(dict[str, object], output),
        message=message,
        source_labels=evidence.source_labels,
        source_count=evidence.source_count,
        source_truncated=evidence.truncated,
        provider_code=provider_result.provider_code,
        model_code=provider_result.model_code,
        input_tokens=provider_result.input_tokens,
        cached_input_tokens=provider_result.cached_input_tokens,
        output_tokens=provider_result.output_tokens,
        fallback_from_provider=provider_result.fallback_from_provider,
        fallback_reason_code=provider_result.fallback_reason_code,
    )


@transaction.atomic
def _requeue_assistant_request(*, request_id: str) -> None:
    assistant_request = ExecutiveAssistantRequest.objects.select_for_update().get(
        pk=request_id
    )
    if assistant_request.status != ExecutiveAssistantRequest.Status.PROCESSING:
        return
    assistant_request.status = ExecutiveAssistantRequest.Status.QUEUED
    assistant_request.started_at = None
    assistant_request.save(update_fields=("status", "started_at", "updated_at"))


@transaction.atomic
def mark_assistant_failed(*, request_id: str, failure_code: str) -> str:
    assistant_request = (
        ExecutiveAssistantRequest.objects.select_for_update()
        .select_related("requested_by")
        .get(pk=request_id)
    )
    if assistant_request.status == ExecutiveAssistantRequest.Status.COMPLETED:
        return assistant_request.status
    if assistant_request.status == ExecutiveAssistantRequest.Status.FAILED:
        return assistant_request.status
    now = timezone.now()
    assistant_request.status = ExecutiveAssistantRequest.Status.FAILED
    assistant_request.started_at = assistant_request.started_at or now
    assistant_request.completed_at = now
    assistant_request.failure_code = failure_code[:64]
    assistant_request.output_data = {}
    assistant_request.save(
        update_fields=(
            "status",
            "started_at",
            "completed_at",
            "failure_code",
            "output_data",
            "updated_at",
        )
    )
    record_audit_event(
        actor=assistant_request.requested_by,
        action=actions.EXECUTIVE_ASSISTANT_FAILED,
        target_type="executive_assistant_request",
        target_id=str(assistant_request.pk),
        target_label="executive_assistant",
        metadata={
            "language": assistant_request.language,
            "status": assistant_request.status,
            "failure_code": assistant_request.failure_code,
        },
        scope=AuditEvent.Scope.EXECUTIVE_BOT,
    )
    return assistant_request.status


def recover_stale_assistant_requests() -> int:
    stale_before = timezone.now() - timedelta(
        minutes=int(settings.EXECUTIVE_ASSISTANT_STALE_MINUTES)
    )
    request_ids = list(
        ExecutiveAssistantRequest.objects.filter(
            status=ExecutiveAssistantRequest.Status.PROCESSING,
            started_at__lt=stale_before,
        )
        .order_by("started_at")
        .values_list("pk", flat=True)[:100]
    )
    recovered: list[str] = []
    for assistant_request_id in request_ids:
        with transaction.atomic():
            assistant_request = (
                ExecutiveAssistantRequest.objects.select_for_update().get(
                    pk=assistant_request_id
                )
            )
            if (
                assistant_request.status != ExecutiveAssistantRequest.Status.PROCESSING
                or assistant_request.started_at is None
                or assistant_request.started_at >= stale_before
            ):
                continue
            assistant_request.status = ExecutiveAssistantRequest.Status.QUEUED
            assistant_request.started_at = None
            assistant_request.save(update_fields=("status", "started_at", "updated_at"))
            recovered.append(str(assistant_request.pk))
    for recovered_request_id in recovered:
        _queue_assistant(recovered_request_id)
    return len(recovered)


def visible_assistant_request(
    *, actor: User, chat_id: str, request_id: str
) -> ExecutiveAssistantRequest:
    if not can_use_executive_assistant(actor, chat_id):
        raise Http404
    try:
        return ExecutiveAssistantRequest.objects.select_related("requested_by").get(
            pk=request_id,
            requested_by=actor,
            chat_id_hash=chat_id_hash(chat_id),
        )
    except (ExecutiveAssistantRequest.DoesNotExist, ValueError) as error:
        raise Http404 from error


def latest_completed_assistant_request(
    *, actor: User, chat_id: str
) -> ExecutiveAssistantRequest:
    if not can_use_executive_assistant(actor, chat_id):
        raise Http404
    assistant_request = (
        ExecutiveAssistantRequest.objects.select_related("requested_by")
        .filter(
            requested_by=actor,
            chat_id_hash=chat_id_hash(chat_id),
            status=ExecutiveAssistantRequest.Status.COMPLETED,
        )
        .order_by("-completed_at", "-created_at")
        .first()
    )
    if assistant_request is None:
        raise Http404
    return assistant_request


def assistant_status_payload(
    assistant_request: ExecutiveAssistantRequest,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "assistant",
        "request_id": str(assistant_request.pk),
        "status": assistant_request.status,
        "language": assistant_request.language,
    }
    if assistant_request.status == ExecutiveAssistantRequest.Status.COMPLETED:
        message = assistant_request.output_data.get("message", "")
        if not isinstance(message, str) or not message:
            raise ValueError("Stored assistant response is invalid.")
        payload["message"] = message[:3900]
    elif assistant_request.status == ExecutiveAssistantRequest.Status.FAILED:
        payload["message"] = (
            "تعذر إعداد الإجابة الآن. يرجى المحاولة لاحقاً."
            if assistant_request.language == ExecutiveAssistantRequest.Language.ARABIC
            else "The answer could not be prepared. Please try again later."
        )
    else:
        payload["message"] = (
            "جاري تحليل السؤال من الأدلة الحالية."
            if assistant_request.language == ExecutiveAssistantRequest.Language.ARABIC
            else "The current evidence is being analyzed."
        )
    return payload


def _critical_fingerprint(task: Task) -> str:
    raw = f"{task.pk}|{task.priority}|{task.status}|{task.due_date}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _critical_message(task: Task) -> str:
    if task.project_id:
        assert task.project is not None
        owner_code = task.project.code
    else:
        assert task.course is not None
        owner_code = task.course.code
    assert task.due_date is not None
    today = timezone.localdate()
    if task.due_date < today:
        timing = f"متأخرة {(today - task.due_date).days} يوم"
    elif task.due_date == today:
        timing = "مستحقة اليوم"
    else:
        timing = "مستحقة غداً"
    return (
        "تنبيه مهمة حرجة\n"
        f"{task.code} - {task.localized_name('ar')}\n"
        f"السياق: {owner_code}\n"
        f"الحالة: {task.get_status_display()}\n"
        f"الموعد: {format_dual_date(task.due_date, 'ar')} ({timing})"
    )


def discover_critical_alerts(*, actor: User, chat_id: str) -> int:
    if not can_use_executive_bot(actor, chat_id) or not actor.has_perm(
        "executive_bot.receive_critical_alert"
    ):
        raise PermissionDenied("Executive bot access is required.")
    created = 0
    with translation.override("ar"):
        for task in critical_tasks_for(actor)[:500]:
            _alert, was_created = CriticalTaskAlert.objects.get_or_create(
                fingerprint=_critical_fingerprint(task),
                defaults={"task": task, "message_ar": _critical_message(task)},
            )
            created += int(was_created)
    return created


@transaction.atomic
def claim_critical_alerts(
    *, actor: User, chat_id: str
) -> tuple[str, list[dict[str, str]]]:
    discover_critical_alerts(actor=actor, chat_id=chat_id)
    now = timezone.now()
    CriticalTaskAlert.objects.filter(
        status=CriticalTaskAlert.Status.LEASED,
        lease_expires_at__lt=now,
    ).update(
        status=CriticalTaskAlert.Status.PENDING,
        lease_digest="",
        lease_expires_at=None,
    )
    alerts = list(
        CriticalTaskAlert.objects.select_for_update(skip_locked=True)
        .filter(status=CriticalTaskAlert.Status.PENDING)
        .select_related("task")
        .order_by("created_at")[: int(settings.EXECUTIVE_BOT_ALERT_BATCH_SIZE)]
    )
    if not alerts:
        return "", []
    lease_token = secrets.token_urlsafe(32)
    lease_digest = hashlib.sha256(lease_token.encode("utf-8")).hexdigest()
    lease_expires_at = now + timedelta(
        seconds=int(settings.EXECUTIVE_BOT_ALERT_LEASE_SECONDS)
    )
    alert_ids = [alert.pk for alert in alerts]
    CriticalTaskAlert.objects.filter(pk__in=alert_ids).update(
        status=CriticalTaskAlert.Status.LEASED,
        lease_digest=lease_digest,
        lease_expires_at=lease_expires_at,
        attempts=F("attempts") + 1,
    )
    return lease_token, [
        {"alert_id": str(alert.pk), "message_ar": alert.message_ar} for alert in alerts
    ]


@transaction.atomic
def acknowledge_critical_alerts(
    *, actor: User, chat_id: str, lease_token: str, alert_ids: list[str]
) -> int:
    if not can_use_executive_bot(actor, chat_id) or not actor.has_perm(
        "executive_bot.receive_critical_alert"
    ):
        raise PermissionDenied("Executive bot access is required.")
    if (
        not lease_token
        or not alert_ids
        or len(alert_ids) > int(settings.EXECUTIVE_BOT_ALERT_BATCH_SIZE)
    ):
        raise ValidationError("Invalid alert acknowledgement.")
    digest = hashlib.sha256(lease_token.encode("utf-8")).hexdigest()
    alerts = list(
        CriticalTaskAlert.objects.select_for_update().filter(pk__in=alert_ids)
    )
    if len(alerts) != len(set(alert_ids)):
        raise ValidationError("Invalid alert acknowledgement.")
    now = timezone.now()
    if any(
        alert.status != CriticalTaskAlert.Status.LEASED
        or alert.lease_expires_at is None
        or alert.lease_expires_at < now
        or not secrets.compare_digest(alert.lease_digest, digest)
        for alert in alerts
    ):
        raise ValidationError("Invalid alert acknowledgement.")
    CriticalTaskAlert.objects.filter(pk__in=[alert.pk for alert in alerts]).update(
        status=CriticalTaskAlert.Status.DELIVERED,
        lease_digest="",
        lease_expires_at=None,
        delivered_at=now,
    )
    record_audit_event(
        actor=actor,
        action=actions.CRITICAL_ALERT_DELIVERED,
        target_type="critical_task_alert",
        target_label="critical_task_alert",
        metadata={"alerts": len(alerts), "status": "delivered"},
        scope=AuditEvent.Scope.EXECUTIVE_BOT,
    )
    return len(alerts)
