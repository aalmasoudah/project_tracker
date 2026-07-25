"""Shared fictional test data."""

from typing import TYPE_CHECKING

import pytest
from django.test import Client

if TYPE_CHECKING:
    from apps.accounts.models import User


@pytest.fixture
def user(db: None) -> "User":
    """Create an active fictional user."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="phase-one-user",
        password="not-a-real-password-9384",
    )


@pytest.fixture
def authenticated_client(client: Client, user: "User") -> Client:
    """Return a Django client with an authenticated session."""
    client.force_login(user)
    return client
