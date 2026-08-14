"""Critical Arabic mobile report generation and English direction coverage."""

import os

import pytest
from django.contrib.auth.models import Permission
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department

PASSWORD = "fictional-browser-password-1307"


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_bilingual_report_page_and_download(live_server: LiveServer) -> None:
    department = Department.objects.create(
        code="BR13",
        name_ar="إدارة تقارير المتصفح",
        name_en="Browser reports",
    )
    user = User.objects.create_user(
        username="browser-phase13-manager",
        email="browser-phase13-manager@example.test",
        display_name="مدير التقارير",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="reports",
            codename__in=("export_project_progress", "export_overdue_tasks"),
        )
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
            accept_downloads=True,
        )
        page = context.new_page()
        page.goto(f"{live_server.url}/accounts/login/")
        page.locator('input[name="username"]').fill(user.username)
        page.locator('input[name="password"]').fill(PASSWORD)
        page.locator('.auth-card button[type="submit"]').click()
        page.wait_for_load_state("networkidle")
        page.goto(f"{live_server.url}/reports/")

        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.locator(".report-logo").is_visible()
        assert page.get_by_role("link", name="إنسايت تراكر").is_visible()
        assert page.locator(".report-logo").get_attribute("alt") == "إنسايت تراكر"
        logo_ratio = page.locator(".report-logo").evaluate(
            "(logo) => ({ rendered: logo.clientWidth / logo.clientHeight, "
            "natural: logo.naturalWidth / logo.naturalHeight })"
        )
        assert logo_ratio["rendered"] == pytest.approx(
            logo_ratio["natural"],
            rel=0.01,
        )
        assert page.locator("body").evaluate(
            "(node) => node.scrollWidth <= node.clientWidth"
        )
        page.locator('select[name="report_type"]').select_option("overdue_tasks")
        assert not page.locator(
            'select[name="output_format"] option[value="pdf"]'
        ).is_disabled()
        page.locator('select[name="output_format"]').select_option("pdf")
        with page.expect_download() as overdue_pdf_download_info:
            page.locator('form[action$="/reports/generate/"] button').click()
        assert overdue_pdf_download_info.value.suggested_filename == (
            "overdue-tasks-ar.pdf"
        )

        page.locator('select[name="output_format"]').select_option("xlsx")
        with page.expect_download() as overdue_download_info:
            page.locator('form[action$="/reports/generate/"] button').click()
        assert overdue_download_info.value.suggested_filename == (
            "overdue-tasks-ar.xlsx"
        )

        page.goto(f"{live_server.url}/reports/")
        page.locator('select[name="report_type"]').select_option("project_progress")
        page.locator('select[name="output_format"]').select_option("xlsx")
        page.locator('select[name="locale"]').select_option("ar")
        with page.expect_download() as download_info:
            page.locator('form[action$="/reports/generate/"] button').click()
        assert download_info.value.suggested_filename == "project-progress-ar.xlsx"

        page.goto(f"{live_server.url}/reports/")
        page.locator('select[name="language"]').select_option("en")
        page.locator('form[action$="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_role("link", name="Insight Tracker").is_visible()
        assert page.get_by_role("heading", name="Reports and exports").is_visible()
        browser.close()
