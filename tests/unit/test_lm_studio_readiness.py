"""Unit tests for the safe local LM Studio readiness command."""

from __future__ import annotations

import json
from email.message import Message
from pathlib import Path
from typing import cast
from urllib.request import Request

import pytest

from scripts import lm_studio_readiness


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, object],
        *,
        headers: Message[str, str] | None = None,
    ) -> None:
        self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.headers = headers or Message()

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, amount: int) -> bytes:
        return self._payload[:amount]


def _configuration(*, api_token: str = "") -> lm_studio_readiness.ProbeConfiguration:
    return lm_studio_readiness.ProbeConfiguration(
        base_url=lm_studio_readiness.APPROVED_BASE_URL,
        model_code=lm_studio_readiness.APPROVED_MODEL_CODE,
        model_id="openai/gpt-oss-20b",
        api_token=api_token,
        timeout_seconds=10,
        reasoning_effort="none",
    )


def test_configuration_rejects_non_loopback_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://0.0.0.0:1234/v1")

    with pytest.raises(
        lm_studio_readiness.ReadinessError,
        match="approved loopback endpoint",
    ):
        lm_studio_readiness.load_configuration(workspace=tmp_path)


def test_configuration_accepts_approved_qwen_with_reasoning_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LM_STUDIO_MODEL_CODE", "qwen/qwen3.5-9b")
    monkeypatch.setenv("LM_STUDIO_MODEL_ID", "qwen/qwen3.5-9b")
    monkeypatch.setenv("LM_STUDIO_REASONING_EFFORT", "none")

    configuration = lm_studio_readiness.load_configuration(workspace=tmp_path)

    assert configuration.model_code == "qwen/qwen3.5-9b"
    assert configuration.model_id == "qwen/qwen3.5-9b"
    assert configuration.reasoning_effort == "none"


def test_configuration_rejects_qwen_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LM_STUDIO_MODEL_CODE", "qwen/qwen3.5-9b")
    monkeypatch.setenv("LM_STUDIO_MODEL_ID", "qwen/qwen3.5-9b")
    monkeypatch.setenv("LM_STUDIO_REASONING_EFFORT", "low")

    with pytest.raises(lm_studio_readiness.ReadinessError, match="requires"):
        lm_studio_readiness.load_configuration(workspace=tmp_path)


def test_loaded_model_ids_requires_exact_advertised_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lm_studio_readiness,
        "urlopen",
        lambda request, timeout: _FakeResponse(
            {"data": [{"id": "openai/gpt-oss-20b-other"}]}
        ),
    )

    with pytest.raises(
        lm_studio_readiness.ReadinessError,
        match="exact configured",
    ):
        lm_studio_readiness.wait_until_ready(
            _configuration(), wait_seconds=0, require_model=True
        )


def test_readiness_sends_optional_token_without_printing_it(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests: list[Request] = []

    def fake_urlopen(request: Request, *, timeout: int) -> _FakeResponse:
        del timeout
        requests.append(request)
        return _FakeResponse({"data": [{"id": "openai/gpt-oss-20b"}]})

    monkeypatch.setattr(lm_studio_readiness, "urlopen", fake_urlopen)
    token = "local-secret-token"
    lm_studio_readiness.wait_until_ready(
        _configuration(api_token=token), wait_seconds=0, require_model=True
    )

    assert requests[0].get_header("Authorization") == f"Bearer {token}"
    assert token not in capsys.readouterr().out


def test_readiness_rejects_cors_enabled_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers: Message[str, str] = Message()
    headers["Access-Control-Allow-Origin"] = "*"
    monkeypatch.setattr(
        lm_studio_readiness,
        "urlopen",
        lambda request, timeout: _FakeResponse({"data": []}, headers=headers),
    )

    with pytest.raises(lm_studio_readiness.ReadinessError, match="CORS"):
        lm_studio_readiness.loaded_model_ids(_configuration())


def test_bilingual_probe_sends_strict_schema_and_validates_both_languages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_payloads: list[dict[str, object]] = []

    def fake_urlopen(request: Request, *, timeout: int) -> _FakeResponse:
        del timeout
        request_data = request.data
        assert isinstance(request_data, bytes)
        payload_value: object = json.loads(request_data)
        assert isinstance(payload_value, dict)
        payload = cast(dict[str, object], payload_value)
        sent_payloads.append(payload)
        messages = payload["messages"]
        assert isinstance(messages, list)
        user_entry = messages[1]
        assert isinstance(user_entry, dict)
        user_message = user_entry["content"]
        assert isinstance(user_message, str)
        is_arabic = "language=ar" in user_message
        content = {
            "language": "ar" if is_arabic else "en",
            "message": "جاهز" if is_arabic else "ready",
            "check_id": "local-json-ready",
        }
        return _FakeResponse(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(content, ensure_ascii=False),
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(lm_studio_readiness, "urlopen", fake_urlopen)

    lm_studio_readiness.run_bilingual_strict_json_probe(_configuration())

    assert len(sent_payloads) == 2
    for payload in sent_payloads:
        response_format = payload["response_format"]
        assert isinstance(response_format, dict)
        assert response_format["type"] == "json_schema"
        json_schema = response_format["json_schema"]
        assert isinstance(json_schema, dict)
        assert json_schema["strict"] is True
        schema = json_schema["schema"]
        assert isinstance(schema, dict)
        assert schema["additionalProperties"] is False
        assert payload["reasoning_effort"] == "none"


def test_bilingual_probe_rejects_markdown_wrapped_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lm_studio_readiness,
        "urlopen",
        lambda request, timeout: _FakeResponse(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '```json\n{"language":"ar"}\n```',
                        },
                    }
                ]
            }
        ),
    )

    with pytest.raises(lm_studio_readiness.ReadinessError, match="prose"):
        lm_studio_readiness.run_bilingual_strict_json_probe(_configuration())
