"""LM Studio provider for read-only strict-schema project briefings."""

from dataclasses import dataclass

from django.conf import settings

from apps.ai_briefings.prompts import SYSTEM_PROMPT, build_user_prompt
from apps.ai_briefings.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderResult,
    TemporaryProviderError,
)
from apps.ai_briefings.providers.lm_studio_transport import (
    LMStudioConfigurationError,
    LMStudioResponseError,
    LMStudioTemporaryError,
    LMStudioTransport,
)
from apps.ai_briefings.schemas import briefing_json_schema


@dataclass(frozen=True, slots=True)
class LMStudioBriefingProvider:
    """Generate one briefing through a loopback-only LM Studio server."""

    transport: LMStudioTransport

    @classmethod
    def from_settings(cls) -> "LMStudioBriefingProvider":
        try:
            transport = LMStudioTransport(
                base_url=str(settings.LM_STUDIO_BASE_URL),
                api_token=str(settings.LM_STUDIO_API_TOKEN),
                model_id=str(settings.LM_STUDIO_MODEL_ID),
                model_code=str(settings.LM_STUDIO_MODEL_CODE),
                reasoning_effort=str(settings.LM_STUDIO_REASONING_EFFORT),
                timeout_seconds=int(settings.LM_STUDIO_TIMEOUT_SECONDS),
                max_output_tokens=int(settings.AI_BRIEFING_MAX_OUTPUT_TOKENS),
                context_length=int(settings.LM_STUDIO_CONTEXT_LENGTH),
                context_token_reserve=int(settings.LM_STUDIO_CONTEXT_TOKEN_RESERVE),
                raw_response_limit=2_000_000,
            )
        except (
            AttributeError,
            TypeError,
            ValueError,
            LMStudioConfigurationError,
        ) as error:
            raise ProviderConfigurationError(
                "LM Studio briefing configuration is invalid."
            ) from error
        return cls(transport=transport)

    def generate(
        self,
        *,
        evidence: dict[str, object],
        language: str,
        detail_level: str,
        repair: bool = False,
    ) -> ProviderResult:
        try:
            result = self.transport.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(
                    evidence=evidence,
                    language=language,
                    detail_level=detail_level,
                    repair=repair,
                ),
                schema_name="project_briefing",
                schema=briefing_json_schema(),
            )
        except LMStudioTemporaryError as error:
            raise TemporaryProviderError(
                str(error),
                retry_after_seconds=error.retry_after_seconds,
            ) from error
        except LMStudioResponseError as error:
            raise ProviderResponseError(
                "LM Studio returned an unusable briefing response."
            ) from error
        return ProviderResult(
            data=result.data,
            provider_code="lm_studio",
            model_code=result.model_code,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            output_tokens=result.output_tokens,
        )
