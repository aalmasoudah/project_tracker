"""Safely verify the approved loopback-only LM Studio endpoint and model."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from http.client import HTTPMessage, HTTPResponse
from pathlib import Path
from typing import IO, Final, cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

APPROVED_BASE_URL: Final = "http://127.0.0.1:1234/v1"
APPROVED_MODEL_CODE: Final = "openai/gpt-oss-20b"
APPROVED_MODEL_CODES: Final = frozenset({APPROVED_MODEL_CODE, "qwen/qwen3.5-9b"})
DEFAULT_MODEL_ID: Final = APPROVED_MODEL_CODE
APPROVED_REASONING_EFFORTS: Final = frozenset({"none", "low", "medium", "high"})
MAX_RESPONSE_BYTES: Final = 1_000_000
_MODEL_ID_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:+\-]{0,199}")


class ReadinessError(RuntimeError):
    """A safe operator-facing readiness failure."""


class _RejectRedirectHandler(HTTPRedirectHandler):
    """Do not let a local endpoint redirect a readiness request."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


_LOCAL_OPENER = build_opener(ProxyHandler({}), _RejectRedirectHandler())
_ENVIRONMENT_NAMES: Final = frozenset(
    {
        "LM_STUDIO_BASE_URL",
        "LM_STUDIO_MODEL_CODE",
        "LM_STUDIO_MODEL_ID",
        "LM_STUDIO_API_TOKEN",
        "LM_STUDIO_TIMEOUT_SECONDS",
        "LM_STUDIO_REASONING_EFFORT",
    }
)


def urlopen(request: Request, *, timeout: int) -> HTTPResponse:
    """Open one local request without proxies or redirects; patchable in tests."""
    return cast(HTTPResponse, _LOCAL_OPENER.open(request, timeout=timeout))


@dataclass(frozen=True, slots=True)
class ProbeConfiguration:
    """Validated local-only readiness configuration."""

    base_url: str
    model_code: str
    model_id: str
    api_token: str
    timeout_seconds: int
    reasoning_effort: str


def _environment_integer(name: str, *, default: int) -> int:
    raw_value = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ReadinessError(f"{name} must be an integer.") from error
    return value


def _load_named_environment_values(path: Path) -> None:
    """Load only LM Studio probe settings without importing other secrets."""
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReadinessError("The local environment file is invalid.") from error
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        normalized_key = key.strip()
        if not separator or not normalized_key:
            raise ReadinessError("The local environment file is invalid.")
        if normalized_key in _ENVIRONMENT_NAMES:
            normalized_value = value.strip().strip("\"'")
            os.environ.setdefault(normalized_key, normalized_value)


def load_configuration(*, workspace: Path) -> ProbeConfiguration:
    """Load only the approved named values, keeping environment precedence."""
    _load_named_environment_values(workspace / ".env")

    base_url = os.environ.get("LM_STUDIO_BASE_URL", APPROVED_BASE_URL).strip()
    if base_url != APPROVED_BASE_URL:
        raise ReadinessError("LM Studio must use the approved loopback endpoint.")

    model_code = os.environ.get("LM_STUDIO_MODEL_CODE", APPROVED_MODEL_CODE).strip()
    if model_code not in APPROVED_MODEL_CODES:
        raise ReadinessError("The configured logical local model is not approved.")

    model_id = os.environ.get("LM_STUDIO_MODEL_ID", DEFAULT_MODEL_ID).strip()
    if _MODEL_ID_PATTERN.fullmatch(model_id) is None:
        raise ReadinessError("The configured LM Studio model identifier is invalid.")

    api_token = os.environ.get("LM_STUDIO_API_TOKEN", "").strip()
    if "\r" in api_token or "\n" in api_token or len(api_token) > 4_096:
        raise ReadinessError("The LM Studio API token configuration is invalid.")

    timeout_seconds = _environment_integer("LM_STUDIO_TIMEOUT_SECONDS", default=180)
    if not 1 <= timeout_seconds <= 600:
        raise ReadinessError("LM_STUDIO_TIMEOUT_SECONDS must be between 1 and 600.")

    reasoning_effort = (
        os.environ.get("LM_STUDIO_REASONING_EFFORT", "none").strip().lower()
    )
    if reasoning_effort not in APPROVED_REASONING_EFFORTS:
        raise ReadinessError("The LM Studio reasoning effort is not approved.")
    if model_code == "qwen/qwen3.5-9b" and reasoning_effort != "none":
        raise ReadinessError("Qwen local inference requires reasoning effort none.")

    return ProbeConfiguration(
        base_url=base_url,
        model_code=model_code,
        model_id=model_id,
        api_token=api_token,
        timeout_seconds=timeout_seconds,
        reasoning_effort=reasoning_effort,
    )


def _request_json(
    *,
    configuration: ProbeConfiguration,
    path: str,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    encoded_payload = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if payload is not None
        else None
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # A CORS-enabled server reflects or allows this origin. The approved
        # local server must not be browser-accessible.
        "Origin": "https://lm-studio-readiness.invalid",
        "User-Agent": "InsightTracker-LMStudio-Readiness/1.0",
    }
    if configuration.api_token:
        headers["Authorization"] = f"Bearer {configuration.api_token}"
    request = Request(
        f"{configuration.base_url}{path}",
        data=encoded_payload,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=configuration.timeout_seconds) as response:
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            raw_response = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        if error.code in {401, 403}:
            raise ReadinessError(
                "LM Studio rejected the local authentication configuration."
            ) from error
        raise ReadinessError("LM Studio returned an unsuccessful response.") from error
    except (OSError, TimeoutError, URLError) as error:
        raise ReadinessError(
            "LM Studio is not reachable on the loopback port."
        ) from error

    if cors_header:
        raise ReadinessError("LM Studio CORS must be disabled for this project.")
    if len(raw_response) > MAX_RESPONSE_BYTES:
        raise ReadinessError("LM Studio returned an oversized readiness response.")
    try:
        parsed: object = json.loads(raw_response)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReadinessError("LM Studio returned invalid readiness JSON.") from error
    if not isinstance(parsed, dict):
        raise ReadinessError("LM Studio returned an invalid readiness envelope.")
    return cast(dict[str, object], parsed)


def loaded_model_ids(configuration: ProbeConfiguration) -> frozenset[str]:
    """Return the exact safe IDs advertised by the local OpenAI endpoint."""
    envelope = _request_json(configuration=configuration, path="/models")
    data = envelope.get("data")
    if not isinstance(data, list):
        raise ReadinessError("LM Studio returned an invalid model list.")
    identifiers: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            raise ReadinessError("LM Studio returned an invalid model entry.")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ReadinessError("LM Studio returned an invalid model identifier.")
        identifiers.add(identifier)
    return frozenset(identifiers)


def wait_until_ready(
    configuration: ProbeConfiguration,
    *,
    wait_seconds: int,
    require_model: bool,
) -> None:
    """Wait for the server and, when requested, the exact configured model."""
    deadline = time.monotonic() + wait_seconds
    last_error: ReadinessError | None = None
    while True:
        try:
            identifiers = loaded_model_ids(configuration)
            if not require_model or configuration.model_id in identifiers:
                return
            last_error = ReadinessError(
                "The exact configured LM Studio model is not visible through "
                "/v1/models."
            )
        except ReadinessError as error:
            last_error = error

        if time.monotonic() >= deadline:
            if last_error is None:
                raise ReadinessError("LM Studio did not become ready in time.")
            raise last_error
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


def _strict_probe(
    configuration: ProbeConfiguration,
    *,
    language: str,
    expected_message: str,
) -> None:
    schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["language", "message", "check_id"],
        "properties": {
            "language": {"type": "string", "const": language},
            "message": {"type": "string", "const": expected_message},
            "check_id": {"type": "string", "const": "local-json-ready"},
        },
    }
    payload: dict[str, object] = {
        "model": configuration.model_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only the JSON object required by the supplied schema. "
                    "Do not add Markdown or explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Complete the bilingual Insight Tracker readiness check. "
                    f"language={language}; message={expected_message}; "
                    "check_id=local-json-ready"
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": f"insight_tracker_readiness_{language}",
                "strict": True,
                "schema": schema,
            },
        },
        "temperature": 0,
        "reasoning_effort": configuration.reasoning_effort,
        "stream": False,
        "max_tokens": 256,
    }
    envelope = _request_json(
        configuration=configuration,
        path="/chat/completions",
        method="POST",
        payload=payload,
    )
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ReadinessError("LM Studio returned an invalid probe response.")
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ReadinessError("LM Studio did not complete the strict JSON probe.")
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("refusal"):
        raise ReadinessError("LM Studio refused the strict JSON probe.")
    content = message.get("content")
    if not isinstance(content, str):
        raise ReadinessError("LM Studio returned invalid strict JSON content.")
    try:
        parsed: object = json.loads(content)
    except json.JSONDecodeError as error:
        raise ReadinessError(
            "LM Studio returned prose instead of strict JSON."
        ) from error
    expected = {
        "language": language,
        "message": expected_message,
        "check_id": "local-json-ready",
    }
    if parsed != expected:
        raise ReadinessError("LM Studio failed application-side schema validation.")


def run_bilingual_strict_json_probe(configuration: ProbeConfiguration) -> None:
    """Verify closed strict-schema output in both approved languages."""
    _strict_probe(configuration, language="ar", expected_message="جاهز")
    _strict_probe(configuration, language="en", expected_message="ready")


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check the approved loopback LM Studio server without printing secrets."
        )
    )
    parser.add_argument(
        "--server-only",
        action="store_true",
        help="Check the loopback server without requiring the configured model.",
    )
    parser.add_argument(
        "--strict-json",
        action="store_true",
        help="Also run the explicit Arabic and English strict JSON-schema probe.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=0,
        help="Wait up to this many seconds for readiness (0-300).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only failures; useful for the one-click launcher.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the safe operator-facing readiness command."""
    arguments = _argument_parser().parse_args(argv)
    if not 0 <= arguments.wait_seconds <= 300:
        print("LM Studio check failed: --wait-seconds must be between 0 and 300.")
        return 2
    if arguments.server_only and arguments.strict_json:
        print("LM Studio check failed: strict JSON requires the configured model.")
        return 2

    workspace = Path(__file__).resolve().parents[1]
    try:
        configuration = load_configuration(workspace=workspace)
        wait_until_ready(
            configuration,
            wait_seconds=arguments.wait_seconds,
            require_model=not arguments.server_only,
        )
        if arguments.strict_json:
            run_bilingual_strict_json_probe(configuration)
    except ReadinessError as error:
        print(f"LM Studio check failed: {error}")
        return 1
    except KeyboardInterrupt:
        print("LM Studio check cancelled.")
        return 130

    if not arguments.quiet:
        if arguments.strict_json:
            print(
                "LM Studio is ready: exact model visible; Arabic/English strict "
                "JSON probes passed."
            )
        elif arguments.server_only:
            print("LM Studio loopback server is ready.")
        else:
            print("LM Studio is ready and the exact configured model is visible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
