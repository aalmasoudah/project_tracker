"""Automated test settings."""

from config.settings.database import postgres_database_from_url
from config.settings.environment import BASE_DIR, env_string

from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key-not-for-production"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": postgres_database_from_url(
        env_string("TEST_DATABASE_URL"),
        require_test_name=True,
    ),
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MEDIA_ROOT = BASE_DIR / "tmp" / "test-media"
