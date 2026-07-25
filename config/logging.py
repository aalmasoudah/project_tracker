"""Structured, secret-aware logging helpers."""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|secret(?:_key)?|token|authorization|cookie|database_url)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
STRUCTURED_FIELDS = (
    "database",
    "event",
    "request_id",
    "status_code",
)


def redact_sensitive_values(value: str) -> str:
    """Redact common secret-bearing key/value pairs from a log string."""
    return SENSITIVE_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        value,
    )


class JsonFormatter(logging.Formatter):
    """Render a stable JSON log record without raw exception details."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_values(record.getMessage()),
        }

        for field_name in STRUCTURED_FIELDS:
            field_value = getattr(record, field_name, None)
            if field_value is not None:
                payload[field_name] = (
                    redact_sensitive_values(field_value)
                    if isinstance(field_value, str)
                    else field_value
                )

        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_logging_config(*, json_logs: bool) -> dict[str, Any]:
    """Build Django's logging configuration for the selected output format."""
    formatter_name = "json" if json_logs else "console"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "format": "%(levelname)s %(name)s %(message)s",
            },
            "json": {
                "()": "config.logging.JsonFormatter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "loggers": {
            "django.server": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
