"""Secret-free settings used only while building deployment assets."""

from .development import *

DEBUG = False
SECRET_KEY = "django-insecure-container-build-only"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
