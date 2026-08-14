from email.message import Message
from uuid import uuid4

import pytest
from django.test import override_settings

from apps.ai_briefings.providers.groq_rate_limits import (
    GroqCapacityUnavailable,
    estimate_groq_input_tokens,
    reserve_groq_capacity,
    retry_after_seconds,
)


def _body(text: str = "مرحبا") -> dict[str, object]:
    return {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": "Return strict JSON."},
            {"role": "user", "content": text},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"],
                    "additionalProperties": False,
                },
            },
        },
        "reasoning_effort": "high",
    }


@pytest.mark.unit
@override_settings(
    GROQ_RATE_LIMITER_ENABLED=False,
    GROQ_RATE_LIMIT_RPM=30,
    GROQ_RATE_LIMIT_RPD=1_000,
    GROQ_RATE_LIMIT_TPM=8_000,
    GROQ_RATE_LIMIT_TPD=200_000,
    GROQ_RATE_LIMIT_TOKEN_RESERVE=256,
    GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS=512,
    GROQ_RATE_LIMIT_WINDOW_SECONDS=60,
)
def test_adaptive_completion_ceiling_accounts_for_prompt_and_reserve() -> None:
    body = _body("أعطني تقريرًا عربيًا موثقًا عن حالة المشروع")
    estimated_input = estimate_groq_input_tokens(body)

    reservation = reserve_groq_capacity(
        api_key=f"fictional-{uuid4().hex}",
        model="openai/gpt-oss-120b",
        body=body,
        configured_output_tokens=7_950,
    )

    assert reservation.estimated_input_tokens == estimated_input
    assert reservation.max_output_tokens == 8_000 - 256 - estimated_input
    assert reservation.max_output_tokens < 7_950
    assert reservation.reserved_tokens <= 8_000 - 256


@pytest.mark.unit
@override_settings(
    CELERY_BROKER_URL="memory://",
    GROQ_RATE_LIMITER_ENABLED=True,
    GROQ_RATE_LIMIT_RPM=30,
    GROQ_RATE_LIMIT_RPD=1_000,
    GROQ_RATE_LIMIT_TPM=2_000,
    GROQ_RATE_LIMIT_TPD=200_000,
    GROQ_RATE_LIMIT_TOKEN_RESERVE=100,
    GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS=256,
    GROQ_RATE_LIMIT_WINDOW_SECONDS=60,
)
def test_reconciliation_releases_unused_capacity_for_next_request() -> None:
    api_key = f"fictional-{uuid4().hex}"
    body = _body()
    first = reserve_groq_capacity(
        api_key=api_key,
        model="openai/gpt-oss-120b",
        body=body,
        configured_output_tokens=1_000,
    )
    first.reconcile(input_tokens=120, cached_input_tokens=20, output_tokens=100)

    second = reserve_groq_capacity(
        api_key=api_key,
        model="openai/gpt-oss-120b",
        body=body,
        configured_output_tokens=1_000,
    )

    assert second.max_output_tokens == 1_000
    second.release()


@pytest.mark.unit
@override_settings(
    CELERY_BROKER_URL="memory://",
    GROQ_RATE_LIMITER_ENABLED=True,
    GROQ_RATE_LIMIT_RPM=30,
    GROQ_RATE_LIMIT_RPD=1_000,
    GROQ_RATE_LIMIT_TPM=1_000,
    GROQ_RATE_LIMIT_TPD=200_000,
    GROQ_RATE_LIMIT_TOKEN_RESERVE=100,
    GROQ_RATE_LIMIT_MIN_OUTPUT_TOKENS=256,
    GROQ_RATE_LIMIT_WINDOW_SECONDS=60,
)
def test_recent_usage_defers_instead_of_sending_a_request_that_would_exceed_tpm() -> (
    None
):
    api_key = f"fictional-{uuid4().hex}"
    body = _body()
    first = reserve_groq_capacity(
        api_key=api_key,
        model="openai/gpt-oss-120b",
        body=body,
        configured_output_tokens=700,
    )

    with pytest.raises(GroqCapacityUnavailable) as captured:
        reserve_groq_capacity(
            api_key=api_key,
            model="openai/gpt-oss-120b",
            body=body,
            configured_output_tokens=700,
        )

    assert 1 <= captured.value.retry_after_seconds <= 60
    first.release()


@pytest.mark.unit
def test_retry_delay_prefers_provider_headers() -> None:
    headers = Message()
    headers["x-ratelimit-reset-tokens"] = "7.66s"
    assert retry_after_seconds(headers) == 9

    headers = Message()
    headers["retry-after"] = "2"
    assert retry_after_seconds(headers) == 3
