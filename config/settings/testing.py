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
CELERY_BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
DEPLOYMENT_ENVIRONMENT = "test"
AI_BRIEFING_ENABLED = True
AI_BRIEFING_PROVIDER = "fake"
EXECUTIVE_BOT_ENABLED = True
EXECUTIVE_BOT_CEO_USERNAME = "phase16-ceo"
EXECUTIVE_BOT_TELEGRAM_CHAT_ID = "123456789"
EXECUTIVE_BOT_SIGNING_SECRET = "test-only-executive-bot-signing-secret"
EXECUTIVE_ASSISTANT_ENABLED = True
PROJECT_AGENT_ENABLED = True
PROJECT_AGENT_PROVIDER = "fake"
PROJECT_AGENT_N8N_ENABLED = True
PROJECT_AGENT_N8N_SIGNING_SECRET = "test-only-project-agent-n8n-signing-secret"
