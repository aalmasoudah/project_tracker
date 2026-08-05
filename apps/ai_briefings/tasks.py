"""Bounded retry wrapper for AI briefing generation."""

# Celery does not publish PEP 561 type metadata.
from celery import Task, shared_task  # type: ignore[import-untyped]

from apps.ai_briefings.providers.base import TemporaryProviderError
from apps.ai_briefings.services import (
    generate_briefing,
    mark_briefing_failed,
    recover_stale_briefings,
)


@shared_task(bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def generate_ai_briefing(self: Task, briefing_id: int) -> str:
    try:
        return generate_briefing(briefing_id=briefing_id)
    except TemporaryProviderError as error:
        if self.request.retries >= self.max_retries:
            return mark_briefing_failed(
                briefing_id=briefing_id,
                failure_code="provider_retry_exhausted",
            )
        countdown = 30 * (2**self.request.retries)
        raise self.retry(
            exc=RuntimeError("AI briefing provider is temporarily unavailable."),
            countdown=countdown,
        ) from error


@shared_task  # type: ignore[untyped-decorator]
def recover_stale_ai_briefings() -> int:
    return recover_stale_briefings()
