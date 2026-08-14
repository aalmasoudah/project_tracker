"""Phase 17 provider selection that fails closed."""

from django.conf import settings

from apps.project_agents.providers.base import (
    AgentProvider,
    ProviderConfigurationError,
)
from apps.project_agents.providers.fake import FakeAgentProvider
from apps.project_agents.providers.groq import GroqAgentProvider
from apps.project_agents.providers.lm_studio import LMStudioAgentProvider


def get_agent_provider(
    *, model_code: str, provider_code: str | None = None
) -> AgentProvider:
    selected_provider = provider_code or str(settings.PROJECT_AGENT_PROVIDER)
    if selected_provider == "fake":
        if settings.DEPLOYMENT_ENVIRONMENT not in {"development", "test"}:
            raise ProviderConfigurationError(
                "The fake project-agent provider is limited to development and test."
            )
        return FakeAgentProvider(model_code=model_code)
    if selected_provider == "groq":
        return GroqAgentProvider.from_settings(model_code=model_code)
    if selected_provider == "lm_studio":
        if settings.DEPLOYMENT_ENVIRONMENT != "development":
            raise ProviderConfigurationError(
                "The LM Studio project-agent provider is limited to local development."
            )
        return LMStudioAgentProvider.from_settings(model_code=model_code)
    raise ProviderConfigurationError("The project-agent provider is disabled.")


__all__ = ["get_agent_provider"]
