"""Provider selection that fails closed."""

from django.conf import settings

from apps.ai_briefings.providers.base import (
    BriefingProvider,
    ProviderConfigurationError,
)
from apps.ai_briefings.providers.fake import FakeBriefingProvider
from apps.ai_briefings.providers.groq import GroqBriefingProvider
from apps.ai_briefings.providers.lm_studio import LMStudioBriefingProvider


def get_briefing_provider() -> BriefingProvider:
    provider_code = str(settings.AI_BRIEFING_PROVIDER)
    if provider_code == "fake":
        if settings.DEPLOYMENT_ENVIRONMENT not in {"development", "test"}:
            raise ProviderConfigurationError(
                "The fake AI provider is limited to development and test."
            )
        return FakeBriefingProvider()
    if provider_code == "groq":
        return GroqBriefingProvider.from_settings()
    if provider_code == "lm_studio":
        if settings.DEPLOYMENT_ENVIRONMENT != "development":
            raise ProviderConfigurationError(
                "The LM Studio AI provider is limited to local development."
            )
        return LMStudioBriefingProvider.from_settings()
    raise ProviderConfigurationError("The AI briefing provider is disabled.")


__all__ = ["get_briefing_provider"]
