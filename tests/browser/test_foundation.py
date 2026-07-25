"""Playwright smoke coverage for Arabic and English foundation pages."""

import os

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_authenticated_shell_switches_between_rtl_and_ltr(
    live_server: LiveServer,
) -> None:
    user = User.objects.create_user(
        username="browser-user",
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
            name="الأساس الهندسي جاهز",
        ).is_visible()
        assert page.evaluate("typeof window.htmx") == "object"
        assert "Noto Sans Arabic" in page.locator("body").evaluate(
            "(element) => getComputedStyle(element).fontFamily"
        )

        page.select_option("#language-select", "en")
        page.locator("button[type=submit]").click()
        page.wait_for_load_state("networkidle")

        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_role(
            "heading",
            name="Engineering foundation ready",
        ).is_visible()

        health_response = page.request.get(f"{live_server.url}/health/")
        assert health_response.status == 200
        assert health_response.json() == {"database": "ok", "status": "ok"}

        context.close()
        browser.close()
