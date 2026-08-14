"""Production settings fail-closed tests."""

import json
import os
import subprocess
import sys
from collections.abc import Mapping

import pytest


def production_environment() -> dict[str, str]:
    """Return safe fictional configuration for importing production settings."""
    environment = os.environ.copy()
    environment.update(
        {
            "ALLOWED_HOSTS": "tracker.example.test",
            "APP_BASE_URL": "https://tracker.example.test",
            "CELERY_BROKER_URL": "rediss://redis.example.test:6379/0",
            "DATABASE_URL": ("postgresql://tracker:password@localhost:5432/tracker"),
            "DEFAULT_LANGUAGE": "ar",
            "DEPLOYMENT_ENVIRONMENT": "production",
            "DEFAULT_FROM_EMAIL": "tracker@example.test",
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "EMAIL_HOST": "smtp.example.test",
            "EMAIL_HOST_PASSWORD": "fictional-smtp-password",
            "EMAIL_HOST_USER": "tracker@example.test",
            "EMAIL_PORT": "587",
            "EMAIL_USE_TLS": "true",
            "LM_STUDIO_FALLBACK_ENABLED": "false",
            "SECRET_KEY": "fictional-production-key-with-sufficient-length-123",
            "AWS_STORAGE_BUCKET_NAME": "fictional-private-bucket",
            "AWS_ACCESS_KEY_ID": "fictional-access-key",
            "AWS_SECRET_ACCESS_KEY": "fictional-secret-key",
        }
    )
    return environment


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("LM_STUDIO_FALLBACK_ENABLED", "true"),
        ("AI_BRIEFING_PROVIDER", "lm_studio"),
        ("PROJECT_AGENT_PROVIDER", "lm_studio"),
    ),
)
def test_production_rejects_local_lm_studio(name: str, value: str) -> None:
    environment = production_environment()
    environment[name] = value

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert "LM Studio" in result.stderr


def run_production_settings(
    environment: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Import production settings in a clean Python process."""
    script = (
        "import json; "
        "from config.settings import production as s; "
        "print(json.dumps({"
        "'debug': s.DEBUG, "
        "'secure_cookie': s.SESSION_COOKIE_SECURE, "
        "'ssl_redirect': s.SECURE_SSL_REDIRECT, "
        "'proxy_header': getattr(s, 'SECURE_PROXY_SSL_HEADER', None), "
        "'redirect_exempt': s.SECURE_REDIRECT_EXEMPT, "
        "'language': s.LANGUAGE_CODE"
        "}))"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        env=dict(environment),
        text=True,
    )


@pytest.mark.unit
@pytest.mark.security
def test_production_settings_are_secure_and_localized() -> None:
    result = run_production_settings(production_environment())

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "debug": False,
        "language": "ar",
        "proxy_header": None,
        "redirect_exempt": ["^health/$"],
        "secure_cookie": True,
        "ssl_redirect": True,
    }


@pytest.mark.unit
@pytest.mark.security
def test_production_proxy_header_requires_explicit_trust() -> None:
    environment = production_environment()
    environment["TRUST_X_FORWARDED_PROTO"] = "true"

    result = run_production_settings(environment)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["proxy_header"] == ["HTTP_X_FORWARDED_PROTO", "https"]


@pytest.mark.unit
@pytest.mark.security
def test_production_worker_requires_groq_key_when_ai_is_enabled() -> None:
    environment = production_environment()
    environment.update(
        {
            "AI_BRIEFING_ENABLED": "true",
            "AI_BRIEFING_PROVIDER": "groq",
            "DEPLOYMENT_PROCESS_ROLE": "worker",
        }
    )
    environment.pop("GROQ_API_KEY", None)

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert "worker requires GROQ_API_KEY" in result.stderr


@pytest.mark.unit
@pytest.mark.security
def test_production_web_does_not_require_worker_groq_key() -> None:
    environment = production_environment()
    environment.update(
        {
            "AI_BRIEFING_ENABLED": "true",
            "AI_BRIEFING_PROVIDER": "groq",
            "DEPLOYMENT_PROCESS_ROLE": "web",
        }
    )
    environment.pop("GROQ_API_KEY", None)

    result = run_production_settings(environment)

    assert result.returncode == 0, result.stderr


@pytest.mark.unit
@pytest.mark.security
def test_production_rejects_unknown_process_role() -> None:
    environment = production_environment()
    environment["DEPLOYMENT_PROCESS_ROLE"] = "unknown"

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert "DEPLOYMENT_PROCESS_ROLE" in result.stderr


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    "missing_name",
    [
        "ALLOWED_HOSTS",
        "APP_BASE_URL",
        "CELERY_BROKER_URL",
        "EMAIL_HOST",
        "SECRET_KEY",
    ],
)
def test_production_settings_reject_missing_critical_values(
    missing_name: str,
) -> None:
    environment = production_environment()
    environment.pop(missing_name)

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert missing_name in result.stderr


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize(
    ("name", "value", "expected_error"),
    [
        ("APP_BASE_URL", "http://tracker.example.test", "HTTPS origin"),
        ("EMAIL_USE_TLS", "false", "EMAIL_USE_TLS"),
        ("DEFAULT_FROM_EMAIL", "invalid-address", "DEFAULT_FROM_EMAIL"),
    ],
)
def test_production_settings_reject_unsafe_notification_configuration(
    name: str,
    value: str,
    expected_error: str,
) -> None:
    environment = production_environment()
    environment[name] = value

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert expected_error in result.stderr
