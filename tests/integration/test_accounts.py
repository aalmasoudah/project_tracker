"""Custom user foundation tests."""

import pytest

from apps.accounts.models import User


@pytest.mark.integration
@pytest.mark.django_db
def test_custom_user_password_is_hashed() -> None:
    raw_password = "fictional-password-9301"
    user = User.objects.create_user(
        username="hash-test-user",
        password=raw_password,
    )

    assert user.password != raw_password
    assert user.check_password(raw_password)
    assert user._meta.label == "accounts.User"
