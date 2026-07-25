"""PostgreSQL-only settings validation."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.database import postgres_database_from_url


@pytest.mark.unit
def test_postgresql_url_is_accepted() -> None:
    config = postgres_database_from_url(
        "postgresql://tracker:password@localhost:5432/tracker"
    )

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "tracker"
    assert config["OPTIONS"]["connect_timeout"] == "3"


@pytest.mark.unit
def test_postgresql_connection_timeout_can_be_overridden() -> None:
    config = postgres_database_from_url(
        "postgresql://tracker:password@localhost:5432/tracker?connect_timeout=7"
    )

    assert config["OPTIONS"]["connect_timeout"] == "7"


@pytest.mark.unit
@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite:///db.sqlite3",
        "mysql://tracker:password@localhost/tracker",
        "postgresql://tracker:password@localhost",
    ],
)
def test_non_postgresql_or_incomplete_url_is_rejected(database_url: str) -> None:
    with pytest.raises(ImproperlyConfigured):
        postgres_database_from_url(database_url)


@pytest.mark.unit
def test_test_database_name_must_end_in_test() -> None:
    with pytest.raises(ImproperlyConfigured, match="ending in '_test'"):
        postgres_database_from_url(
            "postgresql://tracker:password@localhost/tracker",
            require_test_name=True,
        )


@pytest.mark.unit
def test_explicit_test_database_name_is_accepted() -> None:
    config = postgres_database_from_url(
        "postgresql://tracker:password@localhost/tracker_test",
        require_test_name=True,
    )

    assert config["NAME"] == "tracker_test"
