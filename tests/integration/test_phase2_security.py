"""Authentication, lifecycle, audit, and tamper-resistance tests."""

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts.authentication import ACCOUNT_FAILURE_LIMIT
from apps.accounts.models import LoginThrottle, User
from apps.accounts.services import (
    create_account,
    deactivate_account,
    reset_account_password,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.organizations.models import Department
from apps.organizations.services import archive_department


def superuser() -> User:
    return User.objects.create_superuser(
        username="recovery-admin",
        email="recovery-admin@example.test",
        display_name="Recovery Admin",
        password="fictional-admin-password-4561",
    )


def technical_admin(department: Department) -> User:
    user = User.objects.create_user(
        username="technical-admin",
        email="technical-admin@example.test",
        display_name="Technical Admin",
        department=department,
        password="fictional-admin-password-4561",
    )
    user.groups.add(Group.objects.get(name="technical_admin"))
    return user


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_username_authentication_is_case_insensitive_and_inactive_users_fail() -> None:
    user = User.objects.create_user(
        username="Case.User",
        email="case.user@example.test",
        display_name="Case User",
        password="fictional-password-6024",
    )

    assert (
        authenticate(username="case.user", password="fictional-password-6024") == user
    )
    user.is_active = False
    user.save(update_fields=("is_active",))
    assert (
        authenticate(username="CASE.USER", password="fictional-password-6024") is None
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_login_throttle_uses_generic_errors_and_hashed_identifiers(
    client: Client,
) -> None:
    User.objects.create_user(
        username="limited-user",
        email="limited-user@example.test",
        display_name="Limited User",
        password="fictional-password-6024",
    )
    login_url = reverse("accounts:login")
    client.post(
        reverse("set_language"),
        {"language": "en", "next": login_url},
    )

    for _attempt in range(ACCOUNT_FAILURE_LIMIT):
        response = client.post(
            login_url,
            {"username": "limited-user", "password": "wrong-password"},
            REMOTE_ADDR="192.0.2.41",
        )
        assert response.status_code == 200
        assert (
            "Unable to sign in with the provided credentials"
            in response.content.decode()
        )

    locked_response = client.post(
        login_url,
        {
            "username": "limited-user",
            "password": "fictional-password-6024",
        },
        REMOTE_ADDR="192.0.2.41",
    )

    assert locked_response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert LoginThrottle.objects.filter(locked_until__isnull=False).exists()
    assert not LoginThrottle.objects.filter(key_hash__contains="limited-user").exists()
    assert AuditEvent.objects.filter(action=actions.LOGIN_LOCKED).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_temporary_password_forces_change_before_other_pages(client: Client) -> None:
    user = User.objects.create_user(
        username="temporary-user",
        email="temporary-user@example.test",
        display_name="Temporary User",
        must_change_password=True,
        password="old-fictional-password-5902",
    )

    login = client.post(
        reverse("accounts:login"),
        {
            "username": user.username,
            "password": "old-fictional-password-5902",
        },
    )
    assert login["Location"] == reverse("accounts:password_change")
    assert client.get(reverse("home"))["Location"] == reverse(
        "accounts:password_change"
    )

    changed = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "old-fictional-password-5902",
            "new_password1": "new-fictional-password-7830",
            "new_password2": "new-fictional-password-7830",
        },
    )
    user.refresh_from_db()

    assert changed["Location"] == reverse("home")
    assert not user.must_change_password
    assert AuditEvent.objects.filter(
        actor=user,
        action=actions.PASSWORD_CHANGED,
    ).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_deactivation_and_admin_reset_revoke_sessions_and_audit(
    client: Client,
    department: Department,
) -> None:
    actor = technical_admin(department)
    target = User.objects.create_user(
        username="lifecycle-user",
        email="lifecycle-user@example.test",
        display_name="Lifecycle User",
        department=department,
        password="fictional-password-9335",
    )
    target.groups.add(Group.objects.get(name="employee"))
    client.force_login(target)
    first_session = client.session.session_key
    assert first_session is not None

    reset_account_password(
        actor=actor,
        target=target,
        temporary_password="temporary-fictional-password-4816",
    )
    assert not Session.objects.filter(session_key=first_session).exists()
    target.refresh_from_db()
    assert target.must_change_password

    client.force_login(target)
    second_session = client.session.session_key
    deactivate_account(actor=actor, target=target)
    target.refresh_from_db()

    assert not target.is_active
    assert second_session is not None
    assert not Session.objects.filter(session_key=second_session).exists()
    assert set(
        AuditEvent.objects.filter(actor=actor).values_list("action", flat=True)
    ) >= {actions.PASSWORD_RESET, actions.ACCOUNT_DEACTIVATED}


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_technical_admin_cannot_grant_technical_admin(
    department: Department,
) -> None:
    actor = technical_admin(department)

    with pytest.raises(PermissionDenied):
        create_account(
            actor=actor,
            username="escalation-target",
            email="escalation-target@example.test",
            display_name="Escalation Target",
            department=None,
            role_code="technical_admin",
            preferred_language=User.Language.ARABIC,
            temporary_password="fictional-password-4638",
        )

    assert not User.objects.filter(username="escalation-target").exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_final_administrator_and_department_with_active_users_are_protected(
    department: Department,
) -> None:
    final_admin = technical_admin(department)
    actor = User.objects.create_user(
        username="lifecycle-operator",
        email="lifecycle-operator@example.test",
        display_name="Lifecycle Operator",
        department=department,
        password="fictional-password-9853",
    )
    actor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="accounts",
            codename="manage_accounts",
        )
    )

    with pytest.raises(ValidationError):
        deactivate_account(actor=actor, target=final_admin)
    with pytest.raises(ValidationError):
        archive_department(actor=final_admin, department=department)


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_payload_is_sanitized_and_append_only() -> None:
    request = RequestFactory().post(
        "/accounts/login/",
        HTTP_X_REQUEST_ID="request-42",
        REMOTE_ADDR="203.0.113.18",
    )
    event = record_audit_event(
        action=actions.LOGIN_FAILED,
        target_type="authentication",
        metadata={
            "password": "must-not-survive",
            "nested": {"session_token": "must-not-survive", "safe": "value"},
        },
        request=request,
    )

    assert event.correlation_id == "request-42"
    assert event.ip_address == "203.0.113.18"
    assert event.metadata == {"nested": {"safe": "value"}}
    event.action = actions.LOGIN_SUCCEEDED
    with pytest.raises(PermissionDenied):
        event.save()
    with pytest.raises(PermissionDenied):
        AuditEvent.objects.filter(pk=event.pk).update(action=actions.LOGIN_SUCCEEDED)
    with pytest.raises(PermissionDenied):
        AuditEvent.objects.filter(pk=event.pk).delete()
