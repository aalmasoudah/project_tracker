"""Critical Arabic/English mobile browser coverage for Phase 6 progress."""

import os
from datetime import UTC, date, datetime

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.courses.models import Course
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.tasks.models import Task


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_bilingual_progress_details(live_server: LiveServer) -> None:
    executive = User.objects.create_superuser(
        username="browser-phase6-executive",
        email="browser-phase6@example.test",
        display_name="مدير التقدم",
        password="fictional-browser-password-6942",
    )
    department = Department.objects.create(
        code="BRW6",
        name_ar="إدارة متابعة التقدم",
        name_en="Progress Monitoring",
    )
    project = Project.objects.create(
        code="PRJ-BRW6",
        name_ar="مشروع قياس الإنجاز",
        name_en="Achievement Project",
        department=department,
        manager=executive,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=executive,
        updated_by=executive,
    )
    parent = Task.objects.create(
        code="TSK-BR61",
        project=project,
        name_ar="المهمة الرئيسية",
        name_en="Parent Task",
        status=Task.Status.TODO,
        priority=Task.Priority.HIGH,
        created_by=executive,
        updated_by=executive,
    )
    for code, status in (
        ("TSK-BR62", Task.Status.COMPLETED),
        ("TSK-BR63", Task.Status.TODO),
    ):
        Task.objects.create(
            code=code,
            project=project,
            parent=parent,
            name_ar=f"مهمة {code}",
            name_en=f"Task {code}",
            status=status,
            priority=Task.Priority.MEDIUM,
            created_by=executive,
            updated_by=executive,
        )
    course = Course.objects.create(
        code="CRS-BRW6",
        project=project,
        name_ar="دورة الإنجاز",
        name_en="Achievement Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=20,
        start_at=datetime(2026, 9, 1, 8, tzinfo=UTC),
        end_at=datetime(2026, 9, 1, 16, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=executive,
        updated_by=executive,
    )
    excluded_course = Course.objects.create(
        code="CRS-BRW7",
        project=project,
        name_ar="دورة ملغاة",
        name_en="Cancelled Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=20,
        start_at=datetime(2026, 9, 2, 8, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 16, tzinfo=UTC),
        status=Course.Status.CANCELLED,
        created_by=executive,
        updated_by=executive,
    )
    empty_project = Project.objects.create(
        code="PRJ-BRW7",
        name_ar="مشروع بلا مهام",
        name_en="Empty Project",
        department=department,
        manager=executive,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.MEDIUM,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=executive,
        updated_by=executive,
    )
    Task.objects.create(
        code="TSK-BR64",
        course=course,
        name_ar="إكمال الدورة",
        name_en="Complete Course",
        status=Task.Status.COMPLETED,
        priority=Task.Priority.MEDIUM,
        created_by=executive,
        updated_by=executive,
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

        for path, expected in (
            (f"/projects/{project.pk}/", "75,00%"),
            (f"/courses/{course.pk}/", "100,00%"),
            (f"/tasks/{parent.pk}/", "50,00%"),
        ):
            page.goto(f"{live_server.url}{path}", wait_until="networkidle")
            assert page.locator("html").get_attribute("lang") == "ar"
            assert page.locator("html").get_attribute("dir") == "rtl"
            assert page.get_by_text("التقدم", exact=True).is_visible()
            assert page.get_by_text(expected, exact=True).is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.goto(
            f"{live_server.url}/projects/{empty_project.pk}/",
            wait_until="networkidle",
        )
        assert page.get_by_text("لا يوجد عمل قابل للاحتساب", exact=True).is_visible()
        page.goto(
            f"{live_server.url}/courses/{excluded_course.pk}/",
            wait_until="networkidle",
        )
        assert page.get_by_text("لا ينطبق", exact=True).is_visible()

        page.locator(".navbar-toggler").click()
        page.locator("#language-select").select_option("en")
        page.locator('form[action="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_text("Progress", exact=True).is_visible()
        assert page.get_by_text("Not applicable", exact=True).is_visible()
        page.goto(
            f"{live_server.url}/tasks/{parent.pk}/",
            wait_until="networkidle",
        )
        assert page.get_by_text("Progress", exact=True).is_visible()
        assert page.get_by_text("50.00%", exact=True).is_visible()

        context.close()
        browser.close()
