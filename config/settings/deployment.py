"""Security-hardened settings shared by staging and production."""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

from config.settings.database import postgres_database_from_url
from config.settings.environment import env_bool, env_int, env_list, env_string

from .base import *

DEBUG = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
DEPLOYMENT_PROCESS_ROLE = env_string("DEPLOYMENT_PROCESS_ROLE", default="web")
if DEPLOYMENT_PROCESS_ROLE not in {"web", "worker", "scheduler", "release"}:
    raise ImproperlyConfigured(
        "DEPLOYMENT_PROCESS_ROLE must be web, worker, scheduler, or release."
    )
SECRET_KEY = env_string("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("A strong deployment SECRET_KEY is required.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Deployment ALLOWED_HOSTS is required.")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
APP_BASE_URL = env_string("APP_BASE_URL")
app_base_parts = urlsplit(APP_BASE_URL)
if (
    app_base_parts.scheme != "https"
    or not app_base_parts.netloc
    or app_base_parts.path not in ("", "/")
    or app_base_parts.query
    or app_base_parts.fragment
    or app_base_parts.username
    or app_base_parts.password
):
    raise ImproperlyConfigured("Deployment APP_BASE_URL must be an HTTPS origin.")

TRUST_X_FORWARDED_PROTO = env_bool("TRUST_X_FORWARDED_PROTO", default=False)
if TRUST_X_FORWARDED_PROTO:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CELERY_BROKER_URL = env_string("CELERY_BROKER_URL")
if not CELERY_BROKER_URL.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("Deployment CELERY_BROKER_URL must use Redis.")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env_string("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env_string("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env_string("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env_string("DEFAULT_FROM_EMAIL")
if not all(
    (
        EMAIL_HOST,
        EMAIL_PORT,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        DEFAULT_FROM_EMAIL,
    )
):
    raise ImproperlyConfigured(
        "Deployment SMTP configuration is required: EMAIL_HOST, EMAIL_PORT, "
        "EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL."
    )
if not EMAIL_USE_TLS:
    raise ImproperlyConfigured("Deployment SMTP must enable EMAIL_USE_TLS.")
try:
    validate_email(DEFAULT_FROM_EMAIL)
except ValidationError as error:
    raise ImproperlyConfigured(
        "Deployment DEFAULT_FROM_EMAIL must be a valid email address."
    ) from error

if AI_BRIEFING_ENABLED:
    if AI_BRIEFING_PROVIDER != "groq":
        raise ImproperlyConfigured(
            "Deployed AI briefings require AI_BRIEFING_PROVIDER=groq."
        )
    if AI_BRIEFING_MODEL not in {
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    }:
        raise ImproperlyConfigured("Deployed AI briefing model is not approved.")
    if DEPLOYMENT_PROCESS_ROLE == "worker" and not GROQ_API_KEY:
        raise ImproperlyConfigured(
            "The deployed AI briefing worker requires GROQ_API_KEY."
        )

if EXECUTIVE_BOT_ENABLED:
    if not AI_BRIEFING_ENABLED or AI_BRIEFING_PROVIDER != "groq":
        raise ImproperlyConfigured(
            "Deployed executive Telegram reports require the Groq AI feature."
        )

if PROJECT_AGENT_ENABLED:
    if PROJECT_AGENT_PROVIDER != "groq":
        raise ImproperlyConfigured(
            "Deployed project agents require PROJECT_AGENT_PROVIDER=groq."
        )
    if DEPLOYMENT_PROCESS_ROLE == "worker" and not GROQ_API_KEY:
        raise ImproperlyConfigured(
            "The deployed project-agent worker requires GROQ_API_KEY."
        )
    if (
        PROJECT_AGENT_N8N_ENABLED
        and len(PROJECT_AGENT_N8N_SIGNING_SECRET.encode("utf-8")) < 32
    ):
        raise ImproperlyConfigured(
            "Deployed project agents require a 32-byte n8n signing secret."
        )

DATABASES = {
    "default": postgres_database_from_url(
        env_string("DATABASE_URL"),
    ),
}

storage_bucket = env_string("AWS_STORAGE_BUCKET_NAME")
storage_access_key = env_string("AWS_ACCESS_KEY_ID")
storage_secret_key = env_string("AWS_SECRET_ACCESS_KEY")
if not all((storage_bucket, storage_access_key, storage_secret_key)):
    raise ImproperlyConfigured("Private S3 storage credentials are required.")

SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": storage_bucket,
            "access_key": storage_access_key,
            "secret_key": storage_secret_key,
            "endpoint_url": env_string("AWS_S3_ENDPOINT_URL") or None,
            "region_name": env_string("AWS_S3_REGION_NAME") or None,
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
