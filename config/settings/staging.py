"""Staging settings with production-equivalent security controls."""

from django.core.exceptions import ImproperlyConfigured

from .deployment import *

if DEPLOYMENT_ENVIRONMENT != "staging":
    raise ImproperlyConfigured(
        "Staging settings require DEPLOYMENT_ENVIRONMENT=staging."
    )
