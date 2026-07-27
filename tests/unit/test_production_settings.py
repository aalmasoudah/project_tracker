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
            "DATABASE_URL": ("postgresql://tracker:password@localhost:5432/tracker"),
            "DEFAULT_LANGUAGE": "ar",
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "SECRET_KEY": "fictional-production-key-with-sufficient-length-123",
            "AWS_STORAGE_BUCKET_NAME": "fictional-private-bucket",
            "AWS_ACCESS_KEY_ID": "fictional-access-key",
            "AWS_SECRET_ACCESS_KEY": "fictional-secret-key",
        }
    )
    return environment


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
        "secure_cookie": True,
        "ssl_redirect": True,
    }


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.parametrize("missing_name", ["ALLOWED_HOSTS", "SECRET_KEY"])
def test_production_settings_reject_missing_critical_values(
    missing_name: str,
) -> None:
    environment = production_environment()
    environment.pop(missing_name)

    result = run_production_settings(environment)

    assert result.returncode != 0
    assert missing_name in result.stderr
