"""Shared fictional test data."""

from typing import TYPE_CHECKING

import pytest
from django.test import Client

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import Department


@pytest.fixture
def department(db: None) -> "Department":
    """Create a fictional bilingual department."""
    from apps.organizations.models import Department

    return Department.objects.create(
        code="ENG",
        name_ar="الهندسة",
        name_en="Engineering",
    )


@pytest.fixture
def user(db: None, department: "Department") -> "User":
    """Create an active fictional user."""
    from apps.accounts.models import User

    return User.objects.create_user(
        username="phase-one-user",
        email="phase-one-user@example.test",
        display_name="Phase One User",
        department=department,
        password="not-a-real-password-9384",
    )


@pytest.fixture
def authenticated_client(client: Client, user: "User") -> Client:
    """Return a Django client with an authenticated session."""
    client.force_login(user)
    return client
