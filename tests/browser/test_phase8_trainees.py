"""Critical Arabic mobile trainee import workflow."""

import os
from datetime import UTC, date, datetime

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.courses.models import Course
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.trainees.models import CourseEnrollment


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_arabic_mobile_preview_confirm_import(live_server: LiveServer) -> None:
    department = Department.objects.create(
        code="BRW8", name_ar="التدريب", name_en="Training"
    )
    manager = User.objects.create_user(
        username="browser-phase8-manager",
        email="browser-phase8-manager@example.test",
        display_name="مدير التدريب",
        department=department,
        password="fictional-browser-password-8124",
        preferred_language="ar",
    )
    manager_group = Group.objects.get_or_create(name="project_manager")[0]
    manager_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="trainees",
            codename__in=(
                "add_courseenrollment",
                "confirm_trainee_import",
                "import_trainees",
                "view_courseenrollment",
                "view_import_history",
                "view_managed_enrollments",
                "view_trainee",
                "view_trainee_contact",
            ),
        )
    )
    manager.groups.add(manager_group)
    supervisor = User.objects.create_user(
        username="browser-phase8-supervisor",
        email="browser-phase8-supervisor@example.test",
        display_name="مشرف التدريب",
        department=department,
        password="fictional-browser-password-8125",
    )
    project = Project.objects.create(
        code="PRJ-BRW8",
        name_ar="مشروع التدريب",
        name_en="Training Project",
        department=department,
        manager=manager,
        supervisor=supervisor,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=manager,
        updated_by=manager,
    )
    Course.objects.create(
        code="CRS-BRW8",
        project=project,
        name_ar="دورة الاستيراد",
        name_en="Import Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=10,
        start_at=datetime(2026, 8, 2, 9, tzinfo=UTC),
        end_at=datetime(2026, 8, 3, 15, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )
    client = Client()
    client.force_login(manager)
    session_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path, headless=True
        )
        context = browser.new_context(
            locale="ar-SA", viewport={"width": 390, "height": 844}
        )
        context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie,
                    "url": live_server.url,
                }
            ]
        )
        page = context.new_page()
        page.goto(f"{live_server.url}/trainees/imports/upload/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.select_option("#id_course", label="CRS-BRW8 - Import Course")
        page.set_input_files(
            "#id_file",
            {
                "name": "متدربون.csv",
                "mimeType": "text/csv",
                "buffer": (
                    "\ufeffالاسم الكامل,رقم الجوال,البريد الإلكتروني\n"  # noqa: RUF001
                    "متدرب خيالي,0500000001,fictional@example.test\n"
                ).encode(),
            },
        )
        page.get_by_role("button", name="إنشاء معاينة").click()
        page.wait_for_load_state("networkidle")
        assert "متدرب خيالي" in page.content()
        page.get_by_role("button", name="تأكيد الاستيراد").click()
        page.wait_for_load_state("networkidle")
        assert "تم تأكيد الاستيراد بنجاح" in page.content()
        browser.close()
    assert CourseEnrollment.objects.get().trainee.full_name == "متدرب خيالي"
