"""Provider-neutral Phase 17 decision interface."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderResult:
    data: object
    provider_code: str
    model_code: str
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderConfigurationError(RuntimeError):
    pass


class TemporaryProviderError(RuntimeError):
    pass


class ProviderResponseError(RuntimeError):
    pass


class AgentProvider(Protocol):
    def decide(self, *, context: dict[str, object]) -> ProviderResult:
        """Return one strict plan, tool, proposal, or final decision."""
        ...
