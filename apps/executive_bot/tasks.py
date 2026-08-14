"""Bounded retry and recovery tasks for executive Telegram reports."""

# Celery does not publish PEP 561 type metadata.
from celery import Task, shared_task  # type: ignore[import-untyped]

from apps.ai_briefings.providers.base import TemporaryProviderError
from apps.executive_bot.authentication import cleanup_expired_nonces
from apps.executive_bot.services import (
    generate_assistant_request,
    generate_report,
    mark_assistant_failed,
    mark_report_failed,
    recover_stale_assistant_requests,
    recover_stale_reports,
)


@shared_task(bind=True, max_retries=4)  # type: ignore[untyped-decorator]
def generate_executive_report(self: Task, report_id: str) -> str:
    try:
        return generate_report(report_id=report_id)
    except TemporaryProviderError as error:
        if self.request.retries >= self.max_retries:
            return mark_report_failed(
                report_id=report_id,
                failure_code="provider_retry_exhausted",
            )
        countdown = error.retry_after_seconds or 30 * (2**self.request.retries)
        raise self.retry(
            exc=RuntimeError("Executive report provider is temporarily unavailable."),
            countdown=countdown,
        ) from error


@shared_task(bind=True, max_retries=4)  # type: ignore[untyped-decorator]
def generate_executive_answer(self: Task, request_id: str) -> str:
    try:
        return generate_assistant_request(request_id=request_id)
    except TemporaryProviderError as error:
        if self.request.retries >= self.max_retries:
            return mark_assistant_failed(
                request_id=request_id,
                failure_code="provider_retry_exhausted",
            )
        countdown = error.retry_after_seconds or 30 * (2**self.request.retries)
        raise self.retry(
            exc=RuntimeError(
                "Executive assistant provider is temporarily unavailable."
            ),
            countdown=countdown,
        ) from error


@shared_task  # type: ignore[untyped-decorator]
def maintain_executive_bot() -> dict[str, int]:
    return {
        "assistant_requests_recovered": recover_stale_assistant_requests(),
        "reports_recovered": recover_stale_reports(),
        "nonces_removed": cleanup_expired_nonces(),
    }
