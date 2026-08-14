"""Critical mobile RTL/LTR Phase 12 workspace workflow."""

import os

import pytest
from django.contrib.auth.models import Group
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department

PASSWORD = "fictional-browser-password-1208"


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_bilingual_workspace_navigation_and_read_only_views(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="BR12",
        name_ar="إدارة مساحة العمل",
        name_en="Workspace",
    )
    user = User.objects.create_user(
        username="browser-phase12-user",
        email="browser-phase12-user@example.test",
        display_name="مستخدم مساحة العمل",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    user.groups.add(Group.objects.get_or_create(name="employee")[0])

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
        page = context.new_page()
        page.goto(f"{live_server.url}/accounts/login/")
        page.locator('input[name="username"]').fill(user.username)
        page.locator('input[name="password"]').fill(PASSWORD)
        page.locator('.auth-card button[type="submit"]').click()
        page.wait_for_load_state("networkidle")

        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.locator("h1").inner_text() == "لوحة المعلومات"
        page.goto(f"{live_server.url}/workspace/kanban/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.get_by_text("للقراءة فقط", exact=True).count() == 1

        page.locator('select[name="language"]').select_option("en")
        page.locator('form[action$="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_text("Read only", exact=True).count() == 1
        browser.close()
