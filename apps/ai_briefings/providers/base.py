"""Provider-neutral AI briefing interface."""

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
    fallback_from_provider: str | None = None
    fallback_reason_code: str | None = None


class ProviderConfigurationError(RuntimeError):
    """Raised for missing or unsafe provider configuration."""


class TemporaryProviderError(RuntimeError):
    """Raised when a bounded Celery retry may succeed."""

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
    """Raised for invalid, refused, or unusable provider responses."""


class BriefingProvider(Protocol):
    def generate(
        self,
        *,
        evidence: dict[str, object],
        language: str,
        detail_level: str,
        repair: bool = False,
    ) -> ProviderResult:
        """Generate one structured briefing without application tools."""
        ...
