"""Critical mobile Arabic browser workflow for Phase 3."""

import os

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.projects.models import Project


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_executive_can_create_a_project(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="DIG",
        name_ar="التحول الرقمي",
        name_en="Digital Transformation",
    )
    manager = User.objects.create_user(
        username="browser-project-manager",
        email="browser-project-manager@example.test",
        display_name="مدير المشروع",
        department=department,
        password="fictional-browser-password-9814",
    )
    manager.groups.add(Group.objects.get_or_create(name="project_manager")[0])
    executive = User.objects.create_superuser(
        username="browser-phase3-executive",
        email="browser-phase3-executive@example.test",
        display_name="المدير التنفيذي",
        password="fictional-browser-password-9814",
    )
    client = Client()
    client.force_login(executive)
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
        page.goto(f"{live_server.url}/projects/create/", wait_until="networkidle")

        assert page.locator("html").get_attribute("lang") == "ar"
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.locator("#id_code").fill("dig-101")
        page.locator("#id_name_ar").fill("منصة الخدمات الرقمية")
        page.locator("#id_name_en").fill("Digital Services Platform")
        page.locator("#id_department").select_option(str(department.pk))
        page.locator("#id_manager").select_option(str(manager.pk))
        page.locator("#id_priority").select_option("high")
        page.locator("#id_start_date").fill("2026-08-01")
        page.locator("#id_end_date").fill("2026-12-31")
        page.locator("#id_budget").fill("250000.00")
        page.locator("#id_goals").fill("تحسين تجربة المستفيد")
        page.locator('button[type="submit"]').filter(has_text="حفظ").click()
        page.wait_for_load_state("networkidle")

        assert page.get_by_role(
            "heading",
            name="منصة الخدمات الرقمية",
        ).is_visible()
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        context.close()
        browser.close()

    project = Project.objects.get(code="DIG-101")
    assert project.manager == manager
    assert project.budget is not None
