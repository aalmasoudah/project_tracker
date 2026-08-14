"""Secure local LM Studio transport for strict JSON-schema completions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from email.message import Message
from http.client import HTTPMessage, HTTPResponse
from typing import IO, Final, cast
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

APPROVED_LM_STUDIO_MODEL_CODES: Final = frozenset(
    {"openai/gpt-oss-20b", "qwen/qwen3.5-9b"}
)
APPROVED_LM_STUDIO_BASE_URL: Final = "http://127.0.0.1:1234/v1"
MIN_OUTPUT_TOKENS: Final = 256
DEFAULT_RAW_RESPONSE_LIMIT: Final = 1_000_000


class LMStudioConfigurationError(RuntimeError):
    """Raised when the local endpoint or model configuration is unsafe."""


class LMStudioTemporaryError(RuntimeError):
    """Raised only for a transport condition eligible for a bounded fallback."""

    fallback_eligible: Final = True

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LMStudioResponseError(RuntimeError):
    """Raised for a permanent refusal or unusable local-model response."""

    fallback_eligible: Final = False


@dataclass(frozen=True, slots=True)
class LMStudioTransportResult:
    """Validated response envelope values without raw provider metadata."""

    data: object
    model_code: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int


def validate_lm_studio_base_url(value: str) -> str:
    """Accept only the approved native-worker loopback LM Studio base URL."""
    if value != APPROVED_LM_STUDIO_BASE_URL:
        raise LMStudioConfigurationError("The LM Studio base URL is not approved.")
    return APPROVED_LM_STUDIO_BASE_URL


def conservative_token_estimate(value: str | bytes) -> int:
    """Count UTF-8 bytes as tokens so missing usage is never undercounted."""
    encoded = value if isinstance(value, bytes) else value.encode("utf-8")
    return max(1, len(encoded))


def lm_studio_grammar_schema(value: object) -> object:
    """Remove unsupported grammar hints; Django still enforces every bound."""
    if isinstance(value, dict):
        return {
            key: lm_studio_grammar_schema(item)
            for key, item in value.items()
            if key != "maxLength"
        }
    if isinstance(value, list):
        return [lm_studio_grammar_schema(item) for item in value]
    return value


def _reported_token_count(value: object, *, estimate: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return max(1, estimate)


def _retry_after_seconds(headers: Message[str, str] | None) -> int | None:
    if headers is None:
        return None
    raw_value = headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        parsed = int(raw_value)
    except ValueError:
        return None
    return max(1, min(parsed, 300))


class _RejectRedirectHandler(HTTPRedirectHandler):
    """Prevent a local server response from redirecting provider evidence."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> Request | None:
        del req, fp, code, msg, headers, newurl
        return None


_LOCAL_OPENER = build_opener(ProxyHandler({}), _RejectRedirectHandler())


def urlopen(request: Request, *, timeout: int) -> HTTPResponse:
    """Open one request without proxies or redirects; kept patchable for tests."""
    return cast(HTTPResponse, _LOCAL_OPENER.open(request, timeout=timeout))


@dataclass(frozen=True, slots=True)
class LMStudioTransport:
    """Small OpenAI-compatible client constrained to a local LM Studio server."""

    base_url: str
    api_token: str
    model_id: str
    model_code: str
    reasoning_effort: str
    timeout_seconds: int
    max_output_tokens: int
    context_length: int
    context_token_reserve: int
    raw_response_limit: int = DEFAULT_RAW_RESPONSE_LIMIT

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", validate_lm_studio_base_url(self.base_url))
        token = self.api_token.strip()
        if "\r" in token or "\n" in token or len(token) > 4_096:
            raise LMStudioConfigurationError("The LM Studio API token is invalid.")
        object.__setattr__(self, "api_token", token)
        model_id = self.model_id.strip()
        if (
            not model_id
            or len(model_id) > 256
            or any(ord(character) < 32 for character in model_id)
        ):
            raise LMStudioConfigurationError("The LM Studio model ID is invalid.")
        object.__setattr__(self, "model_id", model_id)
        if self.model_code not in APPROVED_LM_STUDIO_MODEL_CODES:
            raise LMStudioConfigurationError(
                "The LM Studio logical model is not approved."
            )
        if self.reasoning_effort not in {"none", "low", "medium", "high"}:
            raise LMStudioConfigurationError(
                "The LM Studio reasoning effort is invalid."
            )
        if self.model_code == "qwen/qwen3.5-9b" and self.reasoning_effort != "none":
            raise LMStudioConfigurationError(
                "Qwen 3.5 must disable reasoning for bounded JSON output."
            )
        if not 1 <= self.timeout_seconds <= 600:
            raise LMStudioConfigurationError("The LM Studio timeout is invalid.")
        if not MIN_OUTPUT_TOKENS <= self.max_output_tokens <= 100_000:
            raise LMStudioConfigurationError(
                "The LM Studio output-token limit is invalid."
            )
        if self.context_length < MIN_OUTPUT_TOKENS * 2:
            raise LMStudioConfigurationError(
                "The LM Studio context length is too small."
            )
        if not 0 <= self.context_token_reserve < self.context_length:
            raise LMStudioConfigurationError(
                "The LM Studio context reserve is invalid."
            )
        if not 1_024 <= self.raw_response_limit <= 5_000_000:
            raise LMStudioConfigurationError(
                "The LM Studio response-size limit is invalid."
            )

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, object],
    ) -> LMStudioTransportResult:
        """Request and parse one strict-schema JSON response."""
        body: dict[str, object] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": lm_studio_grammar_schema(schema),
                },
            },
            "temperature": 0.1,
            "reasoning_effort": self.reasoning_effort,
            "stream": False,
            "max_tokens": self.max_output_tokens,
        }
        preliminary_payload = json.dumps(
            body, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        estimated_input_tokens = conservative_token_estimate(preliminary_payload)
        available_output_tokens = (
            self.context_length - estimated_input_tokens - self.context_token_reserve
        )
        bounded_output_tokens = min(
            self.max_output_tokens,
            available_output_tokens,
        )
        if bounded_output_tokens < MIN_OUTPUT_TOKENS:
            raise LMStudioResponseError(
                "The request exceeds the configured local-model context budget."
            )
        body["max_tokens"] = bounded_output_tokens
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "InsightTracker/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        request = Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read(self.raw_response_limit + 1)
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                raise LMStudioTemporaryError(
                    "LM Studio is temporarily unavailable.",
                    retry_after_seconds=_retry_after_seconds(error.headers),
                ) from error
            raise LMStudioResponseError(
                "LM Studio rejected the structured request."
            ) from error
        except (TimeoutError, URLError) as error:
            raise LMStudioTemporaryError(
                "LM Studio is temporarily unavailable."
            ) from error
        if len(raw_response) > self.raw_response_limit:
            raise LMStudioResponseError("LM Studio returned an oversized response.")
        try:
            envelope_value: object = json.loads(raw_response)
            if not isinstance(envelope_value, dict):
                raise TypeError
            envelope = cast(dict[str, object], envelope_value)
            choices = envelope["choices"]
            if not isinstance(choices, list) or not choices:
                raise TypeError
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                raise TypeError
            finish_reason = first_choice.get("finish_reason")
            if finish_reason in {"length", "content_filter"}:
                raise LMStudioResponseError(
                    "LM Studio did not complete the structured response."
                )
            message = first_choice["message"]
            if not isinstance(message, dict):
                raise TypeError
            if message.get("refusal"):
                raise LMStudioResponseError("LM Studio refused the structured request.")
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError
            data: object = json.loads(content)
            usage_value = envelope.get("usage", {})
            usage = (
                cast(dict[str, object], usage_value)
                if isinstance(usage_value, dict)
                else {}
            )
        except LMStudioResponseError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LMStudioResponseError(
                "LM Studio returned an invalid structured response."
            ) from error
        prompt_details = usage.get("prompt_tokens_details")
        cached_value: object = 0
        if isinstance(prompt_details, dict):
            cached_value = prompt_details.get("cached_tokens", 0)
        cached_tokens = (
            cached_value
            if isinstance(cached_value, int)
            and not isinstance(cached_value, bool)
            and cached_value >= 0
            else 0
        )
        return LMStudioTransportResult(
            data=data,
            model_code=self.model_code,
            input_tokens=_reported_token_count(
                usage.get("prompt_tokens"), estimate=estimated_input_tokens
            ),
            cached_input_tokens=cached_tokens,
            output_tokens=_reported_token_count(
                usage.get("completion_tokens"),
                estimate=conservative_token_estimate(content),
            ),
        )
