"""Critical Arabic mobile and English Phase 14 administrative coverage."""

import os

import pytest
from django.contrib.auth.models import Permission
from django.utils import timezone
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.organizations.models import Department

PASSWORD = "fictional-browser-phase14-password-7712"


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_bilingual_audit_archive_and_operations(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="BR14",
        name_ar="إدارة متصفح العمليات",
        name_en="Browser operations",
    )
    archived = Department.objects.create(
        code="OLD-BR14",
        name_ar="إدارة مؤرشفة",
        name_en="Archived department",
        is_archived=True,
        archived_at=timezone.now(),
    )
    user = User.objects.create_user(
        username="browser-phase14-admin",
        email="browser-phase14-admin@example.test",
        display_name="مسؤول العمليات",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    codenames = {
        "add_department",
        "export_security_audit",
        "restore_department",
        "view_archive_center",
        "view_operations_status",
        "view_security_audit",
    }
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    AuditEvent.objects.create(
        scope=AuditEvent.Scope.SECURITY,
        actor=user,
        action=actions.ACCOUNT_UPDATED,
        target_type="account",
        target_id=str(user.pk),
        target_label="مستخدم تجريبي",
        metadata={"status": "active"},
        correlation_id="browser-phase14",
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

        page.goto(f"{live_server.url}/audit/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert page.get_by_role("heading", name="سجل التدقيق").is_visible()
        table_wrapper = page.locator(".table-responsive")
        assert table_wrapper.evaluate(
            """element => {
              const rect = element.getBoundingClientRect();
              const style = getComputedStyle(element);
              return rect.left >= 0
                && rect.right <= document.documentElement.clientWidth
                && ['auto', 'scroll'].includes(style.overflowX);
            }"""
        )
        with page.expect_download() as download_info:
            page.get_by_role("button", name="تصدير CSV منقح").click()
        assert download_info.value.suggested_filename.startswith("audit-export-")

        page.goto(f"{live_server.url}/operations/archives/")
        assert page.get_by_text(archived.code).is_visible()
        assert page.get_by_role("link", name="مراجعة الاستعادة").is_visible()

        page.goto(f"{live_server.url}/operations/")
        assert page.get_by_role("heading", name="العمليات").is_visible()
        assert page.get_by_text("24", exact=True).is_visible()

        page.locator('select[name="language"]').select_option("en")
        page.locator('form[action$="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_role("heading", name="Operations").is_visible()
        browser.close()
