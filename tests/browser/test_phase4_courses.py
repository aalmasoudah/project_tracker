"""Critical Arabic mobile browser workflow for Phase 4."""

import os
from datetime import date

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.courses.models import Course, CourseTrainerAssignment, Trainer
from apps.organizations.models import Department
from apps.projects.models import Project


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_course_and_trainer_workflow(
    live_server: LiveServer,
) -> None:
    executive = User.objects.create_superuser(
        username="browser-phase4-executive",
        email="browser-phase4@example.test",
        display_name="المدير التنفيذي",
        password="fictional-browser-password-4926",
    )
    department = Department.objects.create(
        code="TRN",
        name_ar="التدريب",
        name_en="Training",
    )
    project = Project.objects.create(
        code="PRJ-TRN",
        name_ar="مشروع تطوير المهارات",
        name_en="Skills Development Project",
        department=department,
        manager=executive,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
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
        page.goto(
            f"{live_server.url}/courses/trainers/create/",
            wait_until="networkidle",
        )
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.locator("#id_code").fill("tr-rtl")
        page.locator("#id_name_ar").fill("نورة المدربة")
        page.locator("#id_name_en").fill("Noura Trainer")
        page.locator("#id_email").fill("noura.trainer@example.test")
        page.locator("#id_phone").fill("+966500000001")
        page.locator("#id_organization").fill("أكاديمية المعرفة")
        page.get_by_role("button", name="حفظ").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("heading", name="نورة المدربة").is_visible()

        page.goto(f"{live_server.url}/courses/create/", wait_until="networkidle")
        page.locator("#id_code").fill("crs-rtl")
        page.locator("#id_project").select_option(str(project.pk))
        page.locator("#id_name_ar").fill("دورة القيادة العملية")
        page.locator("#id_name_en").fill("Practical Leadership")
        page.locator("#id_delivery_type").select_option("in_person")
        page.locator("#id_location").fill("مركز التدريب - الرياض")
        page.locator("#id_capacity").fill("30")
        page.locator("#id_start_at").fill("2026-09-01T09:00")
        page.locator("#id_end_at").fill("2026-09-03T15:00")
        page.get_by_role("button", name="حفظ").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role("heading", name="دورة القيادة العملية").is_visible()

        page.get_by_role("link", name="إسناد المدربين").click()
        trainer_option = page.locator("#id_trainers option").filter(has_text="TR-RTL")
        trainer_id = trainer_option.get_attribute("value")
        assert trainer_id is not None
        page.locator("#id_trainers").select_option(trainer_id)
        page.get_by_role("button", name="حفظ").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("نورة المدربة", exact=False).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.locator(".navbar-toggler").click()
        page.locator("#language-select").select_option("en")
        page.locator('form[action="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator("html").get_attribute("dir") == "ltr"

        context.close()
        browser.close()

    course = Course.objects.get(code="CRS-RTL")
    trainer = Trainer.objects.get(code="TR-RTL")
    assert CourseTrainerAssignment.objects.filter(
        course=course,
        trainer=trainer,
        removed_at__isnull=True,
    ).exists()
