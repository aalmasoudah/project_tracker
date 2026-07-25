"""Playwright smoke coverage for Arabic and English Phase 2 pages."""

import os

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_authenticated_shell_switches_between_rtl_and_ltr(
    live_server: LiveServer,
) -> None:
    user = User.objects.create_user(
        username="browser-user",
        email="browser-user@example.test",
        display_name="Browser User",
        password="fictional-browser-password-3298",
    )
    client = Client()
    client.force_login(user)
    session_cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path,
            headless=True,
        )
        context = browser.new_context(locale="ar-SA")
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        page = context.new_page()
        page.goto(f"{live_server.url}/", wait_until="networkidle")

        page.select_option("#language-select", "ar")
        page.get_by_role("button", name="تغيير اللغة").click()
        page.wait_for_load_state("networkidle")

        assert page.locator("html").get_attribute("lang") == "ar"
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.get_by_role(
            "heading",
            name="الحسابات والهيكل التنظيمي",
        ).is_visible()
        assert page.evaluate("typeof window.htmx") == "object"
        assert "Noto Sans Arabic" in page.locator("body").evaluate(
            "(element) => getComputedStyle(element).fontFamily"
        )

        page.select_option("#language-select", "en")
        page.locator('form[action="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")

        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_role(
            "heading",
            name="Accounts and organization",
        ).is_visible()

        health_response = page.request.get(f"{live_server.url}/health/")
        assert health_response.status == 200
        assert health_response.json() == {"database": "ok", "status": "ok"}

        context.close()
        browser.close()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_admin_can_create_an_account(
    live_server: LiveServer,
) -> None:
    admin = User.objects.create_superuser(
        username="browser-admin",
        email="browser-admin@example.test",
        display_name="Browser Admin",
        password="fictional-browser-password-3298",
    )
    department = Department.objects.create(
        code="MOB",
        name_ar="تجربة الجوال",
        name_en="Mobile Testing",
    )
    Group.objects.get_or_create(name="employee")
    client = Client()
    client.force_login(admin)
    session_cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path,
            headless=True,
        )
        context = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        page = context.new_page()
        page.goto(f"{live_server.url}/", wait_until="networkidle")

        page.get_by_role("button", name="إظهار أو إخفاء قائمة التنقل").click()
        page.get_by_role("link", name="الحسابات", exact=True).click()
        page.get_by_role("link", name="إنشاء حساب").click()
        page.locator("#id_username").fill("mobile-created")
        page.locator("#id_display_name").fill("مستخدم تجريبي")
        page.locator("#id_email").fill("mobile-created@example.test")
        page.locator("#id_department").select_option(str(department.pk))
        page.locator("#id_role").select_option("employee")
        page.locator("#id_preferred_language").select_option("ar")
        page.locator("#id_password1").fill("Fictional!Phase2-7935")
        page.locator("#id_password2").fill("Fictional!Phase2-7935")
        page.get_by_role("button", name="حفظ").click()
        page.wait_for_load_state("networkidle")

        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.get_by_role("heading", name="مستخدم تجريبي").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        context.close()
        browser.close()

    created = User.objects.get(username="mobile-created")
    assert created.department == department
    assert created.must_change_password
