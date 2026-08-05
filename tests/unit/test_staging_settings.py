"""Staging settings use the same fail-closed controls as production."""

import subprocess
import sys

import pytest

from tests.unit.test_production_settings import production_environment


def run_staging_settings(
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Import staging settings in an isolated process."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from config.settings import staging as s; "
                "print(s.DEPLOYMENT_ENVIRONMENT, s.DEBUG, s.SESSION_COOKIE_SECURE)"
            ),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )


@pytest.mark.unit
@pytest.mark.security
def test_staging_settings_are_secure_and_environment_specific() -> None:
    environment = production_environment()
    environment.update(
        {
            "DEPLOYMENT_ENVIRONMENT": "staging",
            "DJANGO_SETTINGS_MODULE": "config.settings.staging",
        }
    )

    result = run_staging_settings(environment)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "staging False True"


@pytest.mark.unit
@pytest.mark.security
def test_staging_settings_reject_production_environment_label() -> None:
    environment = production_environment()
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings.staging"

    result = run_staging_settings(environment)

    assert result.returncode != 0
    assert "DEPLOYMENT_ENVIRONMENT=staging" in result.stderr
