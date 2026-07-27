"""Local development settings."""

from config.settings.database import postgres_database_from_url
from config.settings.environment import BASE_DIR, env_list, env_string

from .base import *

DEBUG = True
SECRET_KEY = env_string(
    "SECRET_KEY",
    default="django-insecure-local-development-only",
)
ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "[::1]"],
)

DATABASES = {
    "default": postgres_database_from_url(
        env_string("DATABASE_URL"),
    ),
}

MEDIA_ROOT = BASE_DIR / "private-media"
