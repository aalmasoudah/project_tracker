"""Local-development LM Studio adapter shared by Telegram AI features."""

from django.conf import settings

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


def generate_local_json(
    *,
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict[str, object],
    max_output_tokens: int,
    raw_response_limit: int,
) -> ProviderResult:
    """Generate one strict-schema response through the loopback-only server."""
    if settings.DEPLOYMENT_ENVIRONMENT != "development":
        raise ProviderConfigurationError("LM Studio is limited to local development.")
    try:
        transport = LMStudioTransport(
            base_url=str(settings.LM_STUDIO_BASE_URL),
            api_token=str(settings.LM_STUDIO_API_TOKEN),
            model_id=str(settings.LM_STUDIO_MODEL_ID),
            model_code=str(settings.LM_STUDIO_MODEL_CODE),
            reasoning_effort=str(settings.LM_STUDIO_REASONING_EFFORT),
            timeout_seconds=int(settings.LM_STUDIO_TIMEOUT_SECONDS),
            max_output_tokens=max_output_tokens,
            context_length=int(settings.LM_STUDIO_CONTEXT_LENGTH),
            context_token_reserve=int(settings.LM_STUDIO_CONTEXT_TOKEN_RESERVE),
            raw_response_limit=raw_response_limit,
        )
        result = transport.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_name=schema_name,
            schema=schema,
        )
    except (AttributeError, TypeError, ValueError, LMStudioConfigurationError) as error:
        raise ProviderConfigurationError(
            "LM Studio Telegram configuration is invalid."
        ) from error
    except LMStudioTemporaryError as error:
        raise TemporaryProviderError(
            "LM Studio is temporarily unavailable.",
            retry_after_seconds=error.retry_after_seconds,
            fallback_eligible=False,
            reason_code="local_provider_unavailable",
        ) from error
    except LMStudioResponseError as error:
        raise ProviderResponseError(
            "LM Studio returned an unusable structured response."
        ) from error
    return ProviderResult(
        data=result.data,
        provider_code="lm_studio",
        model_code=result.model_code,
        input_tokens=result.input_tokens,
        cached_input_tokens=result.cached_input_tokens,
        output_tokens=result.output_tokens,
    )
