"""PostgreSQL-backed Arabic persistence, search, and preference tests."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.selectors import users_visible_to
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.organizations.models import Department
from apps.organizations.selectors import departments_visible_to


@pytest.mark.integration
@pytest.mark.django_db
def test_arabic_identity_round_trip_and_normalized_search() -> None:
    department = Department.objects.create(
        code="OPS",
        name_ar="إِدَارة العَمَلِيّات",
        name_en="Operations",
    )
    actor = User.objects.create_user(
        username="مدير.العمليات",
        email="manager@example.test",
        display_name="إِبـرَاهِيم الكاظمي",
        department=department,
        password="fictional-password-7429",
    )
    actor.groups.add(Group.objects.get(name="ceo"))

    actor.refresh_from_db()
    assert actor.display_name == "إِبـرَاهِيم الكاظمي"
    assert list(users_visible_to(actor, search="ابراهيم الکاظمی")) == [actor]
    assert list(departments_visible_to(actor, search="ادارة العمليات")) == [department]


@pytest.mark.integration
@pytest.mark.django_db
def test_language_switch_persists_on_the_user_and_is_audited(
    client: Client,
    user: User,
) -> None:
    client.force_login(user)
    response = client.post(
        reverse("set_language"),
        {"language": "en", "next": reverse("home")},
    )
    user.refresh_from_db()

    assert response.status_code == 302
    assert user.preferred_language == User.Language.ENGLISH
    assert AuditEvent.objects.filter(
        actor=user,
        action=actions.LANGUAGE_CHANGED,
        metadata={"language": "en"},
    ).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_arabic_validation_and_default_rtl_login_page(client: Client) -> None:
    response = client.post(
        reverse("accounts:login"),
        {"username": "غير-موجود", "password": "not-a-real-password"},
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert '<html lang="ar" dir="rtl">' in content
    assert "تعذّر تسجيل الدخول بالبيانات المقدمة" in content
