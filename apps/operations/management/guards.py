"""Shared environment and confirmation protection for operational commands."""

from django.conf import settings
from django.core.management.base import CommandError

from apps.operations.policies import DEPLOYMENT_ENVIRONMENTS


def require_exact_environment(environment: str) -> None:
    if environment not in DEPLOYMENT_ENVIRONMENTS:
        raise CommandError("Unsupported deployment environment.")
    configured = str(settings.DEPLOYMENT_ENVIRONMENT)
    if environment != configured:
        raise CommandError(
            "The requested environment does not match DEPLOYMENT_ENVIRONMENT."
        )


def require_confirmation(
    *,
    provided: str,
    operation: str,
    environment: str,
) -> None:
    expected = f"{operation}:{environment}"
    if provided != expected:
        raise CommandError(f"Confirmation must exactly match: {expected}")
