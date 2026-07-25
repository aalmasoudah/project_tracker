"""Health endpoint integration and safety tests."""

from unittest.mock import MagicMock, patch

import pytest
from django.db import DEFAULT_DB_ALIAS, OperationalError
from django.test import Client
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.django_db
def test_health_reports_application_and_database_health(client: Client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"database": "ok", "status": "ok"}


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_health_failure_is_safe(
    client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_bearing_error = OperationalError(
        "DATABASE_URL=postgresql://user:secret@private-host/production"
    )
    health_connection = MagicMock()
    health_connection.cursor.side_effect = secret_bearing_error

    with (
        patch("config.views.connections") as connections,
        caplog.at_level("WARNING"),
    ):
        connections[DEFAULT_DB_ALIAS].copy.return_value = health_connection
        response = client.get(reverse("health"))

    connections[DEFAULT_DB_ALIAS].copy.assert_called_once_with(alias="health")
    health_connection.close.assert_called_once_with()
    assert response.status_code == 503
    assert response.json() == {
        "database": "unavailable",
        "status": "unhealthy",
    }
    body = response.content.decode()
    logs = caplog.text
    assert "private-host" not in body
    assert "private-host" not in logs
    assert "secret" not in body
    assert "secret" not in logs
