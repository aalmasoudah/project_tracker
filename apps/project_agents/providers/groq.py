"""Minimal Groq strict-schema client for one Phase 17 agent decision."""

import json
from dataclasses import dataclass
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings

from apps.project_agents.prompts import SYSTEM_PROMPT, build_user_prompt
from apps.project_agents.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderResult,
    TemporaryProviderError,
)
from apps.project_agents.schemas import agent_decision_json_schema

APPROVED_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class GroqAgentProvider:
    api_key: str
    model_code: str
    timeout_seconds: int
    max_output_tokens: int
    reasoning_effort: str

    @classmethod
    def from_settings(cls, *, model_code: str) -> "GroqAgentProvider":
        api_key = str(settings.GROQ_API_KEY).strip()
        if not api_key:
            raise ProviderConfigurationError("GROQ_API_KEY is required.")
        if model_code not in APPROVED_MODELS:
            raise ProviderConfigurationError("The Groq model is not approved.")
        parsed = urlsplit(GROQ_URL)
        if parsed.scheme != "https" or parsed.hostname != "api.groq.com":
            raise ProviderConfigurationError("The Groq endpoint is unsafe.")
        return cls(
            api_key=api_key,
            model_code=model_code,
            timeout_seconds=int(settings.PROJECT_AGENT_TIMEOUT_SECONDS),
            max_output_tokens=int(settings.PROJECT_AGENT_MAX_OUTPUT_TOKENS),
            reasoning_effort=str(settings.PROJECT_AGENT_REASONING_EFFORT),
        )

    def decide(self, *, context: dict[str, object]) -> ProviderResult:
        body = {
            "model": self.model_code,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(context)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "project_agent_decision",
                    "strict": True,
                    "schema": agent_decision_json_schema(),
                },
            },
            "temperature": 0.1,
            "max_completion_tokens": self.max_output_tokens,
            "reasoning_effort": self.reasoning_effort,
            "stream": False,
        }
        request = Request(
            GROQ_URL,
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
                raw = response.read(1_000_001)
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                raise TemporaryProviderError(
                    "Groq is temporarily unavailable."
                ) from error
            raise ProviderResponseError("Groq rejected the agent decision.") from error
        except (TimeoutError, URLError) as error:
            raise TemporaryProviderError("Groq is temporarily unavailable.") from error
        if len(raw) > 1_000_000:
            raise ProviderResponseError("Groq returned an oversized response.")
        try:
            envelope = json.loads(raw)
            message = envelope["choices"][0]["message"]
            if message.get("refusal"):
                raise ProviderResponseError("Groq refused the agent decision.")
            data = json.loads(message["content"])
            usage = cast(dict[str, object], envelope.get("usage", {}))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderResponseError("Groq returned an invalid response.") from error
        details = usage.get("prompt_tokens_details")
        cached: object = None
        if isinstance(details, dict):
            cached = details.get("cached_tokens")
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        return ProviderResult(
            data=data,
            provider_code="groq",
            model_code=self.model_code,
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            cached_input_tokens=cached if isinstance(cached, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
        )
