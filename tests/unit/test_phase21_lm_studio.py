"""Phase 21 LM Studio transport, selection, and fallback unit coverage."""

import json
from dataclasses import replace
from datetime import date
from typing import Any, cast
from urllib.request import Request

import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.ai_briefings.providers import get_briefing_provider
from apps.ai_briefings.providers.base import ProviderResult, TemporaryProviderError
from apps.ai_briefings.providers.lm_studio import LMStudioBriefingProvider
from apps.ai_briefings.providers.lm_studio_transport import (
    APPROVED_LM_STUDIO_BASE_URL,
    LMStudioConfigurationError,
    LMStudioTransport,
    conservative_token_estimate,
    lm_studio_grammar_schema,
    validate_lm_studio_base_url,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.executive_bot import assistant_provider
from apps.executive_bot import provider as report_provider
from apps.organizations.models import Department
from apps.project_agents.models import AgentRun
from apps.project_agents.providers import get_agent_provider
from apps.project_agents.providers.base import (
    ProviderResult as AgentProviderResult,
)
from apps.project_agents.providers.base import (
    TemporaryProviderError as AgentTemporaryProviderError,
)
from apps.project_agents.providers.fake import FakeAgentProvider
from apps.project_agents.providers.lm_studio import LMStudioAgentProvider
from apps.project_agents.schemas import AgentSchemaError
from apps.project_agents.services import (
    _pin_local_agent_fallback,
    process_agent_run,
)
from apps.projects.models import Project


def _valid_briefing_output() -> dict[str, object]:
    return {
        "summary": "Safe concise summary.",
        "highlights": [],
        "risks": [],
        "upcoming": [],
        "recommended_actions": [],
        "data_gaps": [],
    }


class _LMStudioResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_LMStudioResponse":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, limit: int) -> bytes:
        assert limit > 1_024
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


@pytest.mark.unit
@pytest.mark.parametrize(
    "unsafe_url",
    (
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1/",
        "http://0.0.0.0:1234/v1",
        "http://192.168.1.20:1234/v1",
        "https://127.0.0.1:1234/v1",
        "http://127.0.0.1:1234/v1?target=remote",
    ),
)
def test_lm_studio_accepts_only_the_exact_loopback_url(unsafe_url: str) -> None:
    assert (
        validate_lm_studio_base_url(APPROVED_LM_STUDIO_BASE_URL)
        == "http://127.0.0.1:1234/v1"
    )
    with pytest.raises(LMStudioConfigurationError, match="base URL"):
        validate_lm_studio_base_url(unsafe_url)


@pytest.mark.unit
def test_lm_studio_request_is_strict_bounded_arabic_and_estimates_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer = {"answer": "نسبة الإنجاز الحالية 75%"}
    content = json.dumps(answer, ensure_ascii=False)
    response = _LMStudioResponse(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content},
                }
            ]
        }
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, *, timeout: int) -> _LMStudioResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(
        "apps.ai_briefings.providers.lm_studio_transport.urlopen",
        fake_urlopen,
    )
    context_length = 4_096
    reserve = 256
    maximum_output = 2_000
    transport = LMStudioTransport(
        base_url=APPROVED_LM_STUDIO_BASE_URL,
        api_token="",
        model_id="lmstudio-community/gpt-oss-20b-GGUF",
        model_code="openai/gpt-oss-20b",
        reasoning_effort="none",
        timeout_seconds=45,
        max_output_tokens=maximum_output,
        context_length=context_length,
        context_token_reserve=reserve,
    )
    schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["answer"],
        "properties": {"answer": {"type": "string"}},
    }

    result = transport.complete_json(
        system_prompt="أعد JSON فقط.",
        user_prompt="مرحبا " * 150,
        schema_name="arabic_progress_answer",
        schema=schema,
    )

    request = cast(Request, captured["request"])
    assert request.full_url == ("http://127.0.0.1:1234/v1/chat/completions")
    assert captured["timeout"] == 45
    assert request.get_header("Authorization") is None
    assert isinstance(request.data, bytes)
    payload_text = request.data.decode("utf-8")
    body = json.loads(payload_text)
    assert body["model"] == "lmstudio-community/gpt-oss-20b-GGUF"
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "arabic_progress_answer",
            "strict": True,
            "schema": lm_studio_grammar_schema(schema),
        },
    }
    assert body["stream"] is False
    assert body["reasoning_effort"] == "none"
    assert "tools" not in body
    assert "مرحبا" in payload_text
    assert "\\u0645" not in payload_text
    assert 256 <= body["max_tokens"] < maximum_output
    assert body["max_tokens"] + result.input_tokens + reserve <= context_length
    assert result.data == answer
    assert result.model_code == "openai/gpt-oss-20b"
    assert result.cached_input_tokens == 0
    assert result.input_tokens > 0
    assert result.output_tokens == conservative_token_estimate(content)


@pytest.mark.unit
def test_qwen_local_transport_requires_reasoning_disabled() -> None:
    with pytest.raises(LMStudioConfigurationError, match="disable reasoning"):
        LMStudioTransport(
            base_url=APPROVED_LM_STUDIO_BASE_URL,
            api_token="",
            model_id="qwen/qwen3.5-9b",
            model_code="qwen/qwen3.5-9b",
            reasoning_effort="low",
            timeout_seconds=45,
            max_output_tokens=2_000,
            context_length=32_768,
            context_token_reserve=512,
        )


@pytest.mark.unit
@override_settings(
    AI_BRIEFING_PROVIDER="lm_studio",
    DEPLOYMENT_ENVIRONMENT="development",
    LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1",
    LM_STUDIO_API_TOKEN="",
    LM_STUDIO_MODEL_ID="lmstudio-community/gpt-oss-20b-GGUF",
    LM_STUDIO_MODEL_CODE="openai/gpt-oss-20b",
    LM_STUDIO_REASONING_EFFORT="none",
    LM_STUDIO_TIMEOUT_SECONDS=60,
    LM_STUDIO_CONTEXT_LENGTH=16_384,
    LM_STUDIO_CONTEXT_TOKEN_RESERVE=512,
)
def test_briefing_provider_selection_returns_lm_studio_adapter() -> None:
    provider = get_briefing_provider()

    assert isinstance(provider, LMStudioBriefingProvider)
    assert provider.transport.model_id == "lmstudio-community/gpt-oss-20b-GGUF"
    assert provider.transport.model_code == "openai/gpt-oss-20b"


@pytest.mark.unit
@override_settings(
    PROJECT_AGENT_PROVIDER="lm_studio",
    DEPLOYMENT_ENVIRONMENT="development",
    LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1",
    LM_STUDIO_API_TOKEN="",
    LM_STUDIO_MODEL_ID="lmstudio-community/gpt-oss-20b-GGUF",
    LM_STUDIO_MODEL_CODE="openai/gpt-oss-20b",
    LM_STUDIO_REASONING_EFFORT="none",
    LM_STUDIO_TIMEOUT_SECONDS=60,
    LM_STUDIO_CONTEXT_LENGTH=16_384,
    LM_STUDIO_CONTEXT_TOKEN_RESERVE=512,
)
def test_agent_provider_selection_returns_lm_studio_adapter() -> None:
    provider = get_agent_provider(model_code="openai/gpt-oss-20b")

    assert isinstance(provider, LMStudioAgentProvider)
    assert provider.transport.model_id == "lmstudio-community/gpt-oss-20b-GGUF"
    assert provider.transport.model_code == "openai/gpt-oss-20b"


TELEGRAM_GENERATORS = (
    pytest.param(report_provider, "generate_executive_summary", id="report"),
    pytest.param(assistant_provider, "generate_assistant_answer", id="assistant"),
)


def _generate_telegram_output(
    provider_module: Any,
    generator_name: str,
) -> tuple[dict[str, object], ProviderResult]:
    generator = getattr(provider_module, generator_name)
    return cast(
        tuple[dict[str, object], ProviderResult],
        generator(evidence={"items": []}, allowed_citations=frozenset()),
    )


@pytest.mark.unit
@pytest.mark.parametrize(("provider_module", "generator_name"), TELEGRAM_GENERATORS)
@override_settings(
    AI_BRIEFING_PROVIDER="groq",
    LM_STUDIO_FALLBACK_ENABLED=True,
    DEPLOYMENT_ENVIRONMENT="development",
)
def test_telegram_groq_success_never_calls_local_fallback(
    provider_module: Any,
    generator_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"groq": 0, "local": 0}

    def groq_success(**kwargs: object) -> ProviderResult:
        del kwargs
        calls["groq"] += 1
        return ProviderResult(
            data=_valid_briefing_output(),
            provider_code="groq",
            model_code="openai/gpt-oss-120b",
            input_tokens=20,
            output_tokens=10,
        )

    def unexpected_local(**kwargs: object) -> ProviderResult:
        del kwargs
        calls["local"] += 1
        pytest.fail("LM Studio must not run after a successful Groq response.")

    monkeypatch.setattr(provider_module, "_groq_generate", groq_success)
    monkeypatch.setattr(provider_module, "_lm_studio_generate", unexpected_local)

    output, result = _generate_telegram_output(provider_module, generator_name)

    assert output["summary"] == "Safe concise summary."
    assert result.provider_code == "groq"
    assert calls == {"groq": 1, "local": 0}


@pytest.mark.unit
@pytest.mark.parametrize(("provider_module", "generator_name"), TELEGRAM_GENERATORS)
@override_settings(
    AI_BRIEFING_PROVIDER="groq",
    LM_STUDIO_FALLBACK_ENABLED=True,
    DEPLOYMENT_ENVIRONMENT="development",
)
def test_telegram_eligible_groq_failure_uses_local_fallback_once(
    provider_module: Any,
    generator_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"groq": 0, "local": 0}

    def eligible_failure(**kwargs: object) -> ProviderResult:
        del kwargs
        calls["groq"] += 1
        raise TemporaryProviderError(
            "Groq rate capacity is unavailable.",
            fallback_eligible=True,
            reason_code="rate_limited",
        )

    def local_success(**kwargs: object) -> ProviderResult:
        del kwargs
        calls["local"] += 1
        return ProviderResult(
            data=_valid_briefing_output(),
            provider_code="lm_studio",
            model_code="openai/gpt-oss-20b",
            input_tokens=40,
            output_tokens=15,
        )

    monkeypatch.setattr(provider_module, "_groq_generate", eligible_failure)
    monkeypatch.setattr(provider_module, "_lm_studio_generate", local_success)

    _output, result = _generate_telegram_output(provider_module, generator_name)

    assert result.provider_code == "lm_studio"
    assert result.model_code == "openai/gpt-oss-20b"
    assert calls == {"groq": 1, "local": 1}


@pytest.mark.unit
@pytest.mark.parametrize(("provider_module", "generator_name"), TELEGRAM_GENERATORS)
@override_settings(
    AI_BRIEFING_PROVIDER="groq",
    LM_STUDIO_FALLBACK_ENABLED=True,
    DEPLOYMENT_ENVIRONMENT="development",
)
def test_telegram_noneligible_groq_failure_never_calls_local_fallback(
    provider_module: Any,
    generator_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_calls = 0

    def structured_generation_failure(**kwargs: object) -> ProviderResult:
        del kwargs
        raise TemporaryProviderError(
            "Groq produced invalid structured output.",
            fallback_eligible=False,
            reason_code="structured_generation_failed",
        )

    def unexpected_local(**kwargs: object) -> ProviderResult:
        del kwargs
        nonlocal local_calls
        local_calls += 1
        pytest.fail("A noneligible Groq failure must not leave the provider.")

    monkeypatch.setattr(
        provider_module,
        "_groq_generate",
        structured_generation_failure,
    )
    monkeypatch.setattr(provider_module, "_lm_studio_generate", unexpected_local)

    with pytest.raises(
        TemporaryProviderError,
        match="invalid structured output",
    ):
        _generate_telegram_output(provider_module, generator_name)
    assert local_calls == 0


@pytest.mark.unit
@pytest.mark.django_db
@override_settings(
    PROJECT_AGENT_ENABLED=True,
    PROJECT_AGENT_PROVIDER="groq",
    DEPLOYMENT_ENVIRONMENT="development",
    LM_STUDIO_MODEL_CODE="openai/gpt-oss-20b",
    LM_STUDIO_REASONING_EFFORT="none",
    LM_STUDIO_MODEL_ID="lmstudio-community/gpt-oss-20b-GGUF",
    LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1",
    LM_STUDIO_API_TOKEN="",
    LM_STUDIO_TIMEOUT_SECONDS=60,
    LM_STUDIO_CONTEXT_LENGTH=16_384,
    LM_STUDIO_CONTEXT_TOKEN_RESERVE=512,
)
def test_recovery_fallback_pins_provider_and_model_before_local_selection(
    user: User,
    department: Department,
) -> None:
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=("is_staff", "is_superuser"))
    project = Project.objects.create(
        code="PH21-PIN",
        name_ar="مشروع اختبار تثبيت المزود",
        name_en="Provider pin test project",
        department=department,
        manager=user,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 9, 1),
        created_by=user,
        updated_by=user,
    )
    run = AgentRun.objects.create(
        project=project,
        requester=user,
        goal_code=AgentRun.Goal.PROJECT_RECOVERY,
        language=AgentRun.Language.ARABIC,
        provider_code="groq",
        model_code="openai/gpt-oss-120b",
        status=AgentRun.Status.PLANNING,
        max_steps=8,
        max_total_tokens=16_000,
        input_fingerprint="a" * 64,
    )

    pinned = _pin_local_agent_fallback(
        run_id=run.pk,
        reason_code="rate_limited",
    )
    provider = get_agent_provider(
        model_code=pinned.model_code,
        provider_code=pinned.provider_code,
    )

    assert pinned.provider_code == "lm_studio"
    assert pinned.model_code == "openai/gpt-oss-20b"
    assert isinstance(provider, LMStudioAgentProvider)
    event = AuditEvent.objects.get(
        action=actions.AGENT_PROVIDER_FALLBACK,
        target_id=str(run.pk),
    )
    assert event.metadata == {
        "from_provider": "groq",
        "to_provider": "lm_studio",
        "from_model": "openai/gpt-oss-120b",
        "to_model": "openai/gpt-oss-20b",
        "reason_code": "rate_limited",
    }
    with pytest.raises(AgentSchemaError, match="already pinned"):
        _pin_local_agent_fallback(
            run_id=run.pk,
            reason_code="transport_error",
        )


@pytest.mark.unit
@pytest.mark.django_db
@override_settings(
    PROJECT_AGENT_ENABLED=True,
    PROJECT_AGENT_PROVIDER="groq",
    LM_STUDIO_FALLBACK_ENABLED=True,
    DEPLOYMENT_ENVIRONMENT="development",
    LM_STUDIO_MODEL_CODE="qwen/qwen3.5-9b",
)
def test_recovery_run_falls_back_once_and_finishes_at_human_approval(
    user: User,
    department: Department,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=("is_staff", "is_superuser"))
    project = Project.objects.create(
        code="PH21-RUN",
        name_ar="مشروع تحقق التحويل المحلي",
        name_en="Local fallback run",
        department=department,
        manager=user,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 9, 1),
        created_by=user,
        updated_by=user,
    )
    run = AgentRun.objects.create(
        project=project,
        requester=user,
        goal_code=AgentRun.Goal.PROJECT_RECOVERY,
        language=AgentRun.Language.ARABIC,
        model_code="openai/gpt-oss-120b",
        max_steps=8,
        max_total_tokens=50_000,
        input_fingerprint="b" * 64,
    )
    selected_providers: list[str] = []

    class FailingGroqProvider:
        def decide(self, *, context: dict[str, object]) -> AgentProviderResult:
            del context
            raise AgentTemporaryProviderError(
                "Groq is rate limited.",
                fallback_eligible=True,
                reason_code="rate_limited",
            )

    class LocalFakeProvider:
        def __init__(self) -> None:
            self.delegate = FakeAgentProvider(model_code="qwen/qwen3.5-9b")

        def decide(self, *, context: dict[str, object]) -> AgentProviderResult:
            return replace(
                self.delegate.decide(context=context),
                provider_code="lm_studio",
                model_code="qwen/qwen3.5-9b",
            )

    local_provider = LocalFakeProvider()

    def select_provider(*, model_code: str, provider_code: str | None = None) -> object:
        del model_code
        selected = provider_code or "groq"
        selected_providers.append(selected)
        return FailingGroqProvider() if selected == "groq" else local_provider

    monkeypatch.setattr(
        "apps.project_agents.services.get_agent_provider",
        select_provider,
    )

    assert process_agent_run(run_id=run.pk) == AgentRun.Status.AWAITING_APPROVAL
    run.refresh_from_db()
    assert run.provider_code == "lm_studio"
    assert run.model_code == "qwen/qwen3.5-9b"
    assert run.tool_calls.filter(status="completed").count() == 2
    assert run.proposals.filter(status="pending").count() == 1
    assert selected_providers == ["groq", "lm_studio"]
    assert (
        AuditEvent.objects.filter(
            action=actions.AGENT_PROVIDER_FALLBACK,
            target_id=str(run.pk),
        ).count()
        == 1
    )
