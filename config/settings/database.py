"""PostgreSQL-only database configuration helpers."""

from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


def postgres_database_from_url(
    database_url: str,
    *,
    require_test_name: bool = False,
) -> dict[str, Any]:
    """Parse and validate a PostgreSQL database URL."""
    if not database_url:
        raise ImproperlyConfigured("DATABASE_URL is required.")

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL.")

    database_name = parsed.path.removeprefix("/")
    if not database_name:
        raise ImproperlyConfigured("DATABASE_URL must include a database name.")
    if require_test_name and not database_name.lower().endswith("_test"):
        raise ImproperlyConfigured(
            "Test DATABASE_URL must name a database ending in '_test'."
        )

    query_options = {
        key: values[-1]
        for key, values in parse_qs(parsed.query, keep_blank_values=False).items()
        if values
    }
    query_options.setdefault("connect_timeout", "3")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(database_name),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or 5432,
        "OPTIONS": query_options,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
