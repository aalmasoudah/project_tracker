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


class ProviderConfigurationError(RuntimeError):
    """Raised for missing or unsafe provider configuration."""


class TemporaryProviderError(RuntimeError):
    """Raised when a bounded Celery retry may succeed."""


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
