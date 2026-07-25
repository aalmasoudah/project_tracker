"""Authenticated bilingual application shell tests."""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_admin_login(client: Client) -> None:
    response = client.get(reverse("home"))

    assert response.status_code == 302
    assert response["Location"] == "/admin/login/?next=/"


@pytest.mark.integration
@pytest.mark.django_db
def test_authenticated_english_shell_uses_ltr_assets(
    authenticated_client: Client,
) -> None:
    response = authenticated_client.post(
        reverse("set_language"),
        {"language": "en", "next": "/"},
        follow=True,
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert '<html lang="en" dir="ltr">' in content
    assert "bootstrap.min.css" in content
    assert "bootstrap.rtl.min.css" not in content
    assert "htmx.min.js" in content
    assert "Engineering foundation ready" in content


@pytest.mark.integration
@pytest.mark.django_db
def test_authenticated_arabic_shell_uses_rtl_assets(
    authenticated_client: Client,
) -> None:
    response = authenticated_client.post(
        reverse("set_language"),
        {"language": "ar", "next": "/"},
        follow=True,
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert '<html lang="ar" dir="rtl">' in content
    assert "bootstrap.rtl.min.css" in content
    assert "الأساس الهندسي جاهز" in content
    assert "phase-one-user" in content


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_language_switch_rejects_external_return_url(
    authenticated_client: Client,
) -> None:
    response = authenticated_client.post(
        reverse("set_language"),
        {
            "language": "ar",
            "next": "https://attacker.example/collect",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "/"
