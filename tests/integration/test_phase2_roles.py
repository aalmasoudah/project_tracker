"""Phase 2 role seeding, visibility, and navigation tests."""

from collections.abc import Iterable

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.roles import ROLE_CODES
from apps.accounts.selectors import users_visible_to
from apps.organizations.models import Department
from apps.organizations.selectors import departments_visible_to

EXPECTED_PERMISSIONS = {
    "technical_admin": {
        "accounts.add_user",
        "accounts.change_user",
        "accounts.manage_accounts",
        "accounts.view_all_directory",
        "accounts.view_user",
        "audit.export_security_audit",
        "audit.view_auditevent",
        "audit.view_security_audit",
        "organizations.add_department",
        "organizations.archive_department",
        "organizations.change_department",
        "organizations.restore_department",
        "organizations.view_all_departments",
        "organizations.view_department",
    },
    "ceo": {
        "accounts.view_all_directory",
        "accounts.view_user",
        "audit.export_business_audit",
        "audit.view_business_audit",
        "organizations.view_all_departments",
        "organizations.view_department",
        "projects.view_all_projects",
        "projects.view_category",
        "projects.view_client",
        "projects.view_project",
        "projects.view_project_budget",
        "projects.view_project_history",
    },
    "executive_manager": {
        "accounts.view_all_directory",
        "accounts.view_user",
        "audit.export_business_audit",
        "audit.view_business_audit",
        "organizations.view_all_departments",
        "organizations.view_department",
        "projects.add_category",
        "projects.add_client",
        "projects.add_project",
        "projects.archive_category",
        "projects.archive_client",
        "projects.archive_project",
        "projects.change_category",
        "projects.change_client",
        "projects.change_project",
        "projects.manage_project_team",
        "projects.restore_category",
        "projects.restore_client",
        "projects.restore_project",
        "projects.view_all_projects",
        "projects.view_category",
        "projects.view_client",
        "projects.view_project",
        "projects.view_project_budget",
        "projects.view_project_history",
    },
    "project_manager": {
        "accounts.view_department_directory",
        "accounts.view_user",
        "organizations.view_department",
        "projects.add_project",
        "projects.archive_project",
        "projects.change_project",
        "projects.manage_project_team",
        "projects.restore_project",
        "projects.view_category",
        "projects.view_client",
        "projects.view_managed_projects",
        "projects.view_project",
        "projects.view_project_budget",
        "projects.view_project_history",
    },
    "supervisor": {
        "accounts.view_department_directory",
        "accounts.view_user",
        "organizations.view_department",
        "projects.view_assigned_projects",
        "projects.view_project",
    },
    "employee": {
        "accounts.view_own_profile",
        "accounts.view_user",
        "organizations.view_department",
        "projects.view_assigned_projects",
        "projects.view_project",
    },
    "contractor": {
        "accounts.view_own_profile",
        "accounts.view_user",
        "organizations.view_department",
        "projects.view_assigned_projects",
        "projects.view_project",
    },
}


def create_role_user(
    *,
    username: str,
    role: str,
    department: Department,
    active: bool = True,
) -> User:
    """Create a fictional user with one seeded role."""
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        is_active=active,
        password="fictional-password-7209",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def identifiers(users: Iterable[User]) -> set[str]:
    return {user.username for user in users}


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_the_approved_phase3_matrix() -> None:
    assert set(
        Group.objects.filter(name__in=ROLE_CODES).values_list("name", flat=True)
    ) == set(ROLE_CODES)
    for role_code, expected in EXPECTED_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            f"{permission.content_type.app_label}.{permission.codename}"
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label__in=(
                    "accounts",
                    "audit",
                    "organizations",
                    "projects",
                )
            )
        }
        assert actual == expected


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_an_account_cannot_receive_two_managed_roles(
    user: User,
) -> None:
    user.groups.add(Group.objects.get(name="employee"))

    with pytest.raises(ValidationError):
        with transaction.atomic():
            user.groups.add(Group.objects.get(name="contractor"))

    assert list(user.groups.values_list("name", flat=True)) == ["employee"]


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_role_scoped_account_and_department_visibility() -> None:
    engineering = Department.objects.create(
        code="ENG",
        name_ar="الهندسة",
        name_en="Engineering",
    )
    finance = Department.objects.create(
        code="FIN",
        name_ar="المالية",
        name_en="Finance",
    )
    ceo = create_role_user(username="ceo-user", role="ceo", department=engineering)
    manager = create_role_user(
        username="manager-user",
        role="project_manager",
        department=engineering,
    )
    employee = create_role_user(
        username="employee-user",
        role="employee",
        department=engineering,
    )
    create_role_user(
        username="finance-user",
        role="employee",
        department=finance,
    )
    inactive = create_role_user(
        username="inactive-user",
        role="employee",
        department=engineering,
        active=False,
    )

    assert identifiers(users_visible_to(ceo)) == {
        "ceo-user",
        "employee-user",
        "finance-user",
        "manager-user",
    }
    assert identifiers(users_visible_to(manager)) == {
        "ceo-user",
        "employee-user",
        "manager-user",
    }
    assert identifiers(users_visible_to(employee)) == {"employee-user"}
    assert inactive.username not in identifiers(users_visible_to(ceo))
    assert set(departments_visible_to(ceo)) == {engineering, finance}
    assert list(departments_visible_to(manager)) == [engineering]


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_cross_department_detail_is_indistinguishable_from_missing(
    client: Client,
) -> None:
    engineering = Department.objects.create(
        code="ENG",
        name_ar="الهندسة",
        name_en="Engineering",
    )
    finance = Department.objects.create(
        code="FIN",
        name_ar="المالية",
        name_en="Finance",
    )
    manager = create_role_user(
        username="manager-user",
        role="project_manager",
        department=engineering,
    )
    other = create_role_user(
        username="other-user",
        role="employee",
        department=finance,
    )
    client.force_login(manager)

    hidden = client.get(reverse("accounts:detail", args=[other.pk]))
    missing = client.get(reverse("accounts:detail", args=[999_999]))

    assert hidden.status_code == missing.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "accounts_link", "audit_link"),
    [
        ("technical_admin", True, True),
        ("ceo", True, True),
        ("executive_manager", True, True),
        ("project_manager", True, False),
        ("supervisor", True, False),
        ("employee", False, False),
        ("contractor", False, False),
    ],
)
def test_navigation_matches_each_approved_role(
    client: Client,
    department: Department,
    role: str,
    accounts_link: bool,
    audit_link: bool,
) -> None:
    actor = create_role_user(
        username=f"{role}-nav",
        role=role,
        department=department,
    )
    client.force_login(actor)
    response = client.post(
        reverse("set_language"),
        {"language": "en", "next": "/"},
        follow=True,
    )
    content = response.content.decode()

    assert (f'href="{reverse("accounts:list")}"' in content) is accounts_link
    assert (f'href="{reverse("audit:list")}"' in content) is audit_link
    assert f'href="{reverse("organizations:list")}"' in content
