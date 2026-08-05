"""Phase 17 provider selection that fails closed."""

from django.conf import settings

from apps.project_agents.providers.base import (
    AgentProvider,
    ProviderConfigurationError,
)
from apps.project_agents.providers.fake import FakeAgentProvider
from apps.project_agents.providers.groq import GroqAgentProvider


def get_agent_provider(*, model_code: str) -> AgentProvider:
    provider_code = str(settings.PROJECT_AGENT_PROVIDER)
    if provider_code == "fake":
        if settings.DEPLOYMENT_ENVIRONMENT not in {"development", "test"}:
            raise ProviderConfigurationError(
                "The fake project-agent provider is limited to development and test."
            )
        return FakeAgentProvider(model_code=model_code)
    if provider_code == "groq":
        return GroqAgentProvider.from_settings(model_code=model_code)
    raise ProviderConfigurationError("The project-agent provider is disabled.")


__all__ = ["get_agent_provider"]
