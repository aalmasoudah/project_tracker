"""Critical Arabic mobile AI briefing workflow."""

import os
from datetime import date

import pytest
from django.contrib.auth.models import Permission
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.projects.models import Project

PASSWORD = "fictional-browser-phase15-password-2271"


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_ai_briefing_request_and_review(live_server: LiveServer) -> None:
    department = Department.objects.create(
        code="BR15", name_ar="إدارة الموجز", name_en="Briefings"
    )
    manager = User.objects.create_user(
        username="browser-phase15-manager",
        email="browser-phase15-manager@example.test",
        display_name="مدير المشروع التجريبي",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    manager.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label__in={
                "ai_briefings",
                "approvals",
                "projects",
                "tasks",
            },
            codename__in={
                "generate_aibriefing",
                "review_aibriefing",
                "view_aibriefing",
                "view_managed_approvals",
                "view_managed_milestones",
                "view_managed_projects",
                "view_managed_tasks",
                "view_project",
                "view_task",
            },
        )
    )
    project = Project.objects.create(
        code="BRIEF-15",
        name_ar="مشروع الموجز الذكي",
        name_en="AI briefing project",
        department=department,
        manager=manager,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by=manager,
        updated_by=manager,
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
        page.locator('input[name="username"]').fill(manager.username)
        page.locator('input[name="password"]').fill(PASSWORD)
        page.locator('.auth-card button[type="submit"]').click()
        page.wait_for_load_state("networkidle")

        page.goto(f"{live_server.url}/projects/{project.pk}/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.get_by_role("link", name="إنشاء موجز ذكي").click()
        page.locator("#id_language").select_option("ar")
        page.locator('select[name="detail_level"]').select_option("executive")
        page.locator('select[name="evidence_window_days"]').select_option("14")
        page.get_by_role("button", name="إنشاء الموجز").click()
        page.wait_for_load_state("networkidle")

        assert page.get_by_role("heading", name="موجز المشروع الذكي").is_visible()
        assert page.get_by_text("ملخص تجريبي", exact=False).is_visible()
        assert page.get_by_text(
            "مسودة مولدة بالذكاء الاصطناعي", exact=False
        ).is_visible()
        assert page.locator("body").evaluate(
            "element => element.scrollWidth <= document.documentElement.clientWidth"
        )
        page.get_by_role("button", name="وضع علامة تمت المراجعة").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("تمت المراجعة بواسطة", exact=False).is_visible()
        browser.close()
