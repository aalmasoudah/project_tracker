"""Production settings that fail closed on unsafe configuration."""

from django.core.exceptions import ImproperlyConfigured

from config.settings.database import postgres_database_from_url
from config.settings.environment import env_int, env_list, env_string

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
