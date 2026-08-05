"""Transactional request, generation, failure, and review workflows."""

import logging
from datetime import datetime, time, timedelta
from functools import partial
from time import monotonic

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.ai_briefings.evidence import EvidenceBundle, build_project_evidence
from apps.ai_briefings.models import AIBriefing, AIBriefingSource
from apps.ai_briefings.policies import can_generate_briefing, can_review_briefing
from apps.ai_briefings.prompts import PROMPT_VERSION
from apps.ai_briefings.providers import get_briefing_provider
from apps.ai_briefings.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    TemporaryProviderError,
)
from apps.ai_briefings.schemas import (
    BriefingOutput,
    BriefingValidationError,
    validate_briefing_output,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.notifications.services import create_notification
from apps.projects.models import Project

logger = logging.getLogger(__name__)


def _queue_generation(briefing_id: int) -> None:
    try:
        from apps.ai_briefings.tasks import generate_ai_briefing

        generate_ai_briefing.delay(briefing_id)
    except Exception:
        logger.exception(
            "AI briefing enqueue failed.",
            extra={"briefing_id": briefing_id},
        )
        mark_briefing_failed(briefing_id=briefing_id, failure_code="enqueue_failed")


def _local_day_bounds() -> tuple[datetime, datetime]:
    local_date = timezone.localdate()
    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(
        datetime.combine(local_date, time.min), current_timezone
    )
    return start, start + timedelta(days=1)


@transaction.atomic
def request_briefing(
    *,
    actor: User,
    project: Project,
    language: str,
    detail_level: str,
    evidence_window_days: int,
    request: HttpRequest | None = None,
) -> AIBriefing:
    if not can_generate_briefing(actor, project):
        raise PermissionDenied(_("You cannot generate a briefing for this project."))
    if language not in AIBriefing.Language.values:
        raise ValidationError(_("Select a valid briefing language."))
    if detail_level not in AIBriefing.DetailLevel.values:
        raise ValidationError(_("Select a valid detail level."))
    if evidence_window_days not in AIBriefing.EvidenceWindow.values:
        raise ValidationError(_("Select a valid evidence window."))
    User.objects.select_for_update().get(pk=actor.pk)
    day_start, day_end = _local_day_bounds()
    request_count = AIBriefing.objects.filter(
        requested_by=actor,
        created_at__gte=day_start,
        created_at__lt=day_end,
    ).count()
    if request_count >= int(settings.AI_BRIEFING_DAILY_LIMIT):
        raise ValidationError(
            _("You reached today's AI briefing request limit. Try again tomorrow.")
        )
    briefing = AIBriefing.objects.create(
        project=project,
        requested_by=actor,
        language=language,
        detail_level=detail_level,
        evidence_window_days=evidence_window_days,
    )
    record_audit_event(
        actor=actor,
        action=actions.AI_BRIEFING_REQUESTED,
        target_type="ai_briefing",
        target_id=str(briefing.pk),
        target_label=project.code,
        metadata={
            "project_id": project.pk,
            "language": language,
            "detail_level": detail_level,
            "evidence_window_days": evidence_window_days,
            "status": briefing.status,
        },
        request=request,
        scope=AuditEvent.Scope.AI_BRIEFINGS,
    )
    transaction.on_commit(partial(_queue_generation, briefing.pk))
    return briefing


def _validated_provider_output(
    *,
    bundle: EvidenceBundle,
    briefing: AIBriefing,
) -> tuple[BriefingOutput, str, str, int | None, int | None, int | None]:
    provider = get_briefing_provider()
    last_validation_error: BriefingValidationError | None = None
    for repair in (False, True):
        result = provider.generate(
            evidence=bundle.payload,
            language=briefing.language,
            detail_level=briefing.detail_level,
            repair=repair,
        )
        try:
            validated = validate_briefing_output(
                result.data,
                allowed_citations=bundle.allowed_citations,
            )
        except BriefingValidationError as error:
            last_validation_error = error
            continue
        return (
            validated,
            result.provider_code,
            result.model_code,
            result.input_tokens,
            result.cached_input_tokens,
            result.output_tokens,
        )
    raise ProviderResponseError("Provider output failed local validation.") from (
        last_validation_error
    )


def _complete_briefing(
    *,
    briefing: AIBriefing,
    bundle: EvidenceBundle,
    output: BriefingOutput,
    provider_code: str,
    model_code: str,
    input_tokens: int | None,
    cached_input_tokens: int | None,
    output_tokens: int | None,
    duration_ms: int,
) -> str:
    with transaction.atomic():
        locked = AIBriefing.objects.select_for_update().get(pk=briefing.pk)
        if locked.status in (AIBriefing.Status.COMPLETED, AIBriefing.Status.FAILED):
            return locked.status
        AIBriefingSource.objects.bulk_create(
            [
                AIBriefingSource(
                    briefing=locked,
                    source_ref=source.source_ref,
                    source_type=source.source_type,
                    source_id=source.source_id,
                    source_label=source.source_label,
                    source_updated_at=source.source_updated_at,
                )
                for source in bundle.sources
            ]
        )
        locked.status = AIBriefing.Status.COMPLETED
        locked.output_data = output
        locked.provider_code = provider_code
        locked.model_code = model_code
        locked.prompt_version = PROMPT_VERSION
        locked.input_fingerprint = bundle.fingerprint
        locked.evidence_count = len(bundle.sources)
        locked.evidence_truncated = bundle.truncated
        locked.input_tokens = input_tokens
        locked.cached_input_tokens = cached_input_tokens
        locked.output_tokens = output_tokens
        locked.duration_ms = max(0, duration_ms)
        locked.failure_code = ""
        locked.completed_at = timezone.now()
        locked.save(
            update_fields=(
                "status",
                "output_data",
                "provider_code",
                "model_code",
                "prompt_version",
                "input_fingerprint",
                "evidence_count",
                "evidence_truncated",
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "duration_ms",
                "failure_code",
                "completed_at",
                "updated_at",
            )
        )
        record_audit_event(
            actor=locked.requested_by,
            action=actions.AI_BRIEFING_COMPLETED,
            target_type="ai_briefing",
            target_id=str(locked.pk),
            target_label=locked.project.code,
            metadata={
                "project_id": locked.project_id,
                "language": locked.language,
                "status": locked.status,
                "evidence_count": locked.evidence_count,
                "evidence_truncated": locked.evidence_truncated,
                "model_code": locked.model_code,
            },
            scope=AuditEvent.Scope.AI_BRIEFINGS,
        )
        create_notification(
            recipient=locked.requested_by,
            message_code="ai_briefing_ready",
            event_key=f"ai-briefing-ready:{locked.pk}",
            target_path=reverse("ai_briefings:detail", args=(locked.pk,)),
        )
    return AIBriefing.Status.COMPLETED


def generate_briefing(*, briefing_id: int) -> str:
    """Generate idempotently; transient errors are left for the Celery task."""
    with transaction.atomic():
        briefing = (
            AIBriefing.objects.select_for_update()
            .select_related("project", "requested_by")
            .get(pk=briefing_id)
        )
        if briefing.status in (AIBriefing.Status.COMPLETED, AIBriefing.Status.FAILED):
            return briefing.status
        if briefing.status == AIBriefing.Status.PROCESSING:
            return briefing.status
        if briefing.status == AIBriefing.Status.QUEUED:
            briefing.status = AIBriefing.Status.PROCESSING
            briefing.started_at = timezone.now()
            briefing.save(update_fields=("status", "started_at", "updated_at"))
    started = monotonic()
    try:
        if not can_generate_briefing(briefing.requested_by, briefing.project):
            raise PermissionDenied("Current project access is required.")
        bundle = build_project_evidence(
            actor=briefing.requested_by,
            project=briefing.project,
            language=briefing.language,
            window_days=briefing.evidence_window_days,
        )
        (
            output,
            provider_code,
            model_code,
            input_tokens,
            cached_input_tokens,
            output_tokens,
        ) = _validated_provider_output(bundle=bundle, briefing=briefing)
    except TemporaryProviderError:
        _requeue_briefing_for_retry(briefing_id=briefing_id)
        raise
    except PermissionDenied:
        return mark_briefing_failed(
            briefing_id=briefing_id,
            failure_code="access_revoked",
        )
    except ProviderConfigurationError:
        return mark_briefing_failed(
            briefing_id=briefing_id,
            failure_code="provider_unavailable",
        )
    except (ProviderResponseError, BriefingValidationError):
        return mark_briefing_failed(
            briefing_id=briefing_id,
            failure_code="invalid_provider_response",
        )
    except Exception:
        logger.exception(
            "AI briefing generation failed.",
            extra={"briefing_id": briefing_id},
        )
        return mark_briefing_failed(
            briefing_id=briefing_id,
            failure_code="generation_failed",
        )
    duration_ms = int((monotonic() - started) * 1000)
    return _complete_briefing(
        briefing=briefing,
        bundle=bundle,
        output=output,
        provider_code=provider_code,
        model_code=model_code,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    )


@transaction.atomic
def _requeue_briefing_for_retry(*, briefing_id: int) -> None:
    briefing = AIBriefing.objects.select_for_update().get(pk=briefing_id)
    if briefing.status != AIBriefing.Status.PROCESSING:
        return
    briefing.status = AIBriefing.Status.QUEUED
    briefing.started_at = None
    briefing.save(update_fields=("status", "started_at", "updated_at"))


def recover_stale_briefings() -> int:
    """Requeue interrupted processing jobs without duplicating active work."""
    stale_before = timezone.now() - timedelta(
        minutes=int(settings.AI_BRIEFING_STALE_MINUTES)
    )
    briefing_ids = list(
        AIBriefing.objects.filter(
            status=AIBriefing.Status.PROCESSING,
            started_at__lt=stale_before,
        )
        .order_by("started_at", "pk")
        .values_list("pk", flat=True)[:100]
    )
    recovered: list[int] = []
    for briefing_id in briefing_ids:
        with transaction.atomic():
            briefing = AIBriefing.objects.select_for_update().get(pk=briefing_id)
            if (
                briefing.status != AIBriefing.Status.PROCESSING
                or briefing.started_at is None
                or briefing.started_at >= stale_before
            ):
                continue
            briefing.status = AIBriefing.Status.QUEUED
            briefing.started_at = None
            briefing.save(update_fields=("status", "started_at", "updated_at"))
            recovered.append(briefing_id)
    for briefing_id in recovered:
        _queue_generation(briefing_id)
    return len(recovered)


@transaction.atomic
def mark_briefing_failed(*, briefing_id: int, failure_code: str) -> str:
    briefing = (
        AIBriefing.objects.select_for_update()
        .select_related("project", "requested_by")
        .get(pk=briefing_id)
    )
    if briefing.status == AIBriefing.Status.COMPLETED:
        return briefing.status
    if briefing.status == AIBriefing.Status.FAILED:
        return briefing.status
    now = timezone.now()
    briefing.status = AIBriefing.Status.FAILED
    briefing.started_at = briefing.started_at or now
    briefing.completed_at = now
    briefing.failure_code = failure_code[:64]
    briefing.output_data = {}
    briefing.save(
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
        actor=briefing.requested_by,
        action=actions.AI_BRIEFING_FAILED,
        target_type="ai_briefing",
        target_id=str(briefing.pk),
        target_label=briefing.project.code,
        metadata={
            "project_id": briefing.project_id,
            "status": briefing.status,
            "failure_code": briefing.failure_code,
        },
        scope=AuditEvent.Scope.AI_BRIEFINGS,
    )
    return AIBriefing.Status.FAILED


@transaction.atomic
def review_briefing(
    *,
    actor: User,
    briefing: AIBriefing,
    request: HttpRequest | None = None,
) -> AIBriefing:
    briefing = (
        AIBriefing.objects.select_for_update()
        .select_related("project", "requested_by")
        .get(pk=briefing.pk)
    )
    if not can_review_briefing(actor, briefing):
        raise PermissionDenied(_("You cannot review this briefing."))
    briefing.reviewed_by = actor
    briefing.reviewed_at = timezone.now()
    briefing.save(update_fields=("reviewed_by", "reviewed_at", "updated_at"))
    record_audit_event(
        actor=actor,
        action=actions.AI_BRIEFING_REVIEWED,
        target_type="ai_briefing",
        target_id=str(briefing.pk),
        target_label=briefing.project.code,
        metadata={"project_id": briefing.project_id, "status": briefing.status},
        request=request,
        scope=AuditEvent.Scope.AI_BRIEFINGS,
    )
    return briefing
