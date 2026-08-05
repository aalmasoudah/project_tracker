"""Minimal Groq Chat Completions client with strict structured output."""

import json
from dataclasses import dataclass
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings

from apps.ai_briefings.prompts import SYSTEM_PROMPT, build_user_prompt
from apps.ai_briefings.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderResult,
    TemporaryProviderError,
)
from apps.ai_briefings.schemas import briefing_json_schema

APPROVED_GROQ_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class GroqBriefingProvider:
    api_key: str
    model: str
    timeout_seconds: int
    max_output_tokens: int
    reasoning_effort: str

    @classmethod
    def from_settings(cls) -> "GroqBriefingProvider":
        api_key = str(settings.GROQ_API_KEY).strip()
        model = str(settings.AI_BRIEFING_MODEL).strip()
        if not api_key:
            raise ProviderConfigurationError("GROQ_API_KEY is required.")
        if model not in APPROVED_GROQ_MODELS:
            raise ProviderConfigurationError("The Groq model is not approved.")
        parsed = urlsplit(GROQ_CHAT_COMPLETIONS_URL)
        if parsed.scheme != "https" or parsed.hostname != "api.groq.com":
            raise ProviderConfigurationError("The Groq endpoint is unsafe.")
        return cls(
            api_key=api_key,
            model=model,
            timeout_seconds=int(settings.AI_BRIEFING_TIMEOUT_SECONDS),
            max_output_tokens=int(settings.AI_BRIEFING_MAX_OUTPUT_TOKENS),
            reasoning_effort=str(settings.AI_BRIEFING_REASONING_EFFORT),
        )

    def generate(
        self,
        *,
        evidence: dict[str, object],
        language: str,
        detail_level: str,
        repair: bool = False,
    ) -> ProviderResult:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(
                        evidence=evidence,
                        language=language,
                        detail_level=detail_level,
                        repair=repair,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "project_briefing",
                    "strict": True,
                    "schema": briefing_json_schema(),
                },
            },
            "temperature": 0.1,
            "max_completion_tokens": self.max_output_tokens,
            "reasoning_effort": self.reasoning_effort,
            "stream": False,
        }
        request = Request(
            GROQ_CHAT_COMPLETIONS_URL,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read(2_000_001)
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                raise TemporaryProviderError(
                    "Groq is temporarily unavailable."
                ) from error
            raise ProviderResponseError(
                "Groq rejected the briefing request."
            ) from error
        except (TimeoutError, URLError) as error:
            raise TemporaryProviderError("Groq is temporarily unavailable.") from error
        if len(raw_response) > 2_000_000:
            raise ProviderResponseError("Groq returned an oversized response.")
        try:
            envelope = json.loads(raw_response)
            message = envelope["choices"][0]["message"]
            refusal = message.get("refusal")
            if refusal:
                raise ProviderResponseError("Groq refused the briefing request.")
            data = json.loads(message["content"])
            usage = cast(dict[str, object], envelope.get("usage", {}))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderResponseError("Groq returned an invalid response.") from error
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        token_details = usage.get("prompt_tokens_details")
        cached_input_tokens: object = None
        if isinstance(token_details, dict):
            cached_input_tokens = token_details.get("cached_tokens")
        return ProviderResult(
            data=data,
            provider_code="groq",
            model_code=self.model,
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            cached_input_tokens=(
                cached_input_tokens if isinstance(cached_input_tokens, int) else None
            ),
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
        )
