"""Structured logging tests."""

import json
import logging

import pytest

from config.logging import JsonFormatter, redact_sensitive_values


@pytest.mark.unit
def test_sensitive_values_are_redacted() -> None:
    message = "password=unsafe token:abc123 DATABASE_URL=postgresql://user:pass@host/db"

    redacted = redact_sensitive_values(message)

    assert "unsafe" not in redacted
    assert "abc123" not in redacted
    assert "user:pass" not in redacted
    assert redacted.count("[REDACTED]") == 3


@pytest.mark.unit
def test_json_formatter_preserves_arabic_and_structured_fields() -> None:
    record = logging.LogRecord(
        name="tests",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="تم فحص الخدمة token=unsafe",
        args=(),
        exc_info=None,
    )
    record.event = "health_check"
    record.database = "ok"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "تم فحص الخدمة token=[REDACTED]"
    assert payload["event"] == "health_check"
    assert payload["database"] == "ok"
    assert payload["level"] == "INFO"
