"""Critical Arabic/English mobile notification workflow."""

import os

import pytest
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.policies import MESSAGE_CONTENT
from apps.organizations.models import Department

PASSWORD = "fictional-browser-password-1107"


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_bilingual_notification_read_and_preferences(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="BRN11",
        name_ar="إدارة الإشعارات",
        name_en="Notifications",
    )
    user = User.objects.create_user(
        username="browser-phase11-user",
        email="browser-phase11-user@example.test",
        display_name="مستخدم الإشعارات",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    content = MESSAGE_CONTENT["task_assigned"]
    notification = Notification.objects.create(
        recipient=user,
        category=Notification.Category.TASK_ASSIGNMENT,
        message_code="task_assigned",
        event_key="browser:phase11:assignment",
        title_ar=content.title_ar,
        title_en=content.title_en,
        body_ar=content.body_ar,
        body_en=content.body_en,
        target_path="/accounts/me/",
    )

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

        page.goto(f"{live_server.url}/notifications/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert content.title_ar in page.content()
        page.locator(
            f'form[action$="/notifications/{notification.pk}/open/"] button'
        ).click()
        page.wait_for_load_state("networkidle")
        assert page.url.endswith("/accounts/me/")

        page.goto(f"{live_server.url}/notifications/")
        page.locator('select[name="language"]').select_option("en")
        page.locator('form[action$="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert content.title_en in page.content()

        page.goto(f"{live_server.url}/notifications/preferences/")
        assert page.locator('input[name="approval_in_app"]').is_disabled()
        page.locator('input[name="task_assignment_in_app"]').uncheck()
        page.locator('input[name="task_assignment_email"]').uncheck()
        page.get_by_role("button", name="Save preferences").click()
        page.wait_for_load_state("networkidle")
        assert "Notification preferences saved." in page.content()
        browser.close()

    notification.refresh_from_db()
    assert notification.is_read
    preference = NotificationPreference.objects.get(
        recipient=user,
        category=Notification.Category.TASK_ASSIGNMENT,
    )
    assert preference.in_app_enabled is False
    assert preference.email_enabled is False
