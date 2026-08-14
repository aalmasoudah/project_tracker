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
    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: int | None = None,
        fallback_eligible: bool = False,
        reason_code: str = "provider_unavailable",
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.fallback_eligible = fallback_eligible
        self.reason_code = reason_code


class ProviderResponseError(RuntimeError):
    pass


class AgentProvider(Protocol):
    def decide(self, *, context: dict[str, object]) -> ProviderResult:
        """Return one strict plan, tool, proposal, or final decision."""
        ...
