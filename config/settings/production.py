"""Production settings that fail closed on unsafe configuration."""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

from config.settings.database import postgres_database_from_url
from config.settings.environment import env_bool, env_int, env_list, env_string

from .base import *

DEBUG = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
SECRET_KEY = env_string("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("A strong production SECRET_KEY is required.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production ALLOWED_HOSTS is required.")

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
    raise ImproperlyConfigured("Production APP_BASE_URL must be an HTTPS origin.")

CELERY_BROKER_URL = env_string("CELERY_BROKER_URL")
if not CELERY_BROKER_URL.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("Production CELERY_BROKER_URL must use Redis.")

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
        "Production SMTP configuration is required: EMAIL_HOST, EMAIL_PORT, "
        "EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL."
    )
if not EMAIL_USE_TLS:
    raise ImproperlyConfigured("Production SMTP must enable EMAIL_USE_TLS.")
try:
    validate_email(DEFAULT_FROM_EMAIL)
except ValidationError as error:
    raise ImproperlyConfigured(
        "Production DEFAULT_FROM_EMAIL must be a valid email address."
    ) from error

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
