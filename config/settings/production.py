"""Production settings that fail closed on an incorrect environment label."""

from django.core.exceptions import ImproperlyConfigured

from .deployment import *

if DEPLOYMENT_ENVIRONMENT != "production":
    raise ImproperlyConfigured(
        "Production settings require DEPLOYMENT_ENVIRONMENT=production."
    )
