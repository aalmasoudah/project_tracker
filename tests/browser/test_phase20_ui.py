"""Critical Phase 20 Arabic mobile and English desktop UI workflow."""

import os
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, override_settings
from PIL import Image
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.tasks.models import Task


def _png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (720, 480), (10, 64, 12)).save(output, format="PNG")
    return output.getvalue()


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_bilingual_responsive_shell_progress_and_avatar(
    live_server: LiveServer,
    tmp_path: Path,
) -> None:
    executive = User.objects.create_superuser(
        username="phase20-browser",
        email="phase20-browser@example.test",
        display_name="مدير تجربة الواجهة",
        password="fictional-browser-password-2088",
    )
    department = Department.objects.create(
        code="UX20",
        name_ar="إدارة تجربة المستخدم",
        name_en="User Experience",
    )
    project = Project.objects.create(
        code="PRJ-UX20",
        name_ar="مشروع تحسين الواجهة",
        name_en="Interface Improvement",
        department=department,
        manager=executive,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=executive,
        updated_by=executive,
    )
    for code, status in (
        ("TSK-UX201", Task.Status.COMPLETED),
        ("TSK-UX202", Task.Status.TODO),
    ):
        Task.objects.create(
            code=code,
            project=project,
            name_ar=f"مهمة الواجهة {code}",
            name_en=f"Interface task {code}",
            status=status,
            priority=Task.Priority.MEDIUM,
            created_by=executive,
            updated_by=executive,
        )

    client = Client()
    client.force_login(executive)
    session_cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None
    capture_screenshots = os.environ.get("PHASE20_CAPTURE_SCREENSHOTS") == "1"
    screenshot_directory = Path(settings.BASE_DIR) / "tmp" / "phase20-visual-review"
    if capture_screenshots:
        screenshot_directory.mkdir(parents=True, exist_ok=True)

    with override_settings(MEDIA_ROOT=tmp_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path,
            headless=True,
        )
        mobile = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        mobile.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        page = mobile.new_page()
        page.goto(f"{live_server.url}/", wait_until="networkidle")

        assert page.locator("html").get_attribute("dir") == "rtl"
        assert "width: 50.00%" in (
            page.locator(".app-progress .progress-bar").first.get_attribute("style")
            or ""
        )
        page.goto(
            f"{live_server.url}/projects/{project.pk}/",
            wait_until="networkidle",
        )
        assert (
            page.locator(".progress-ring-value").get_attribute("stroke-dasharray")
            == "50.00 100"
        )
        page.goto(f"{live_server.url}/", wait_until="networkidle")
        page.locator(".navbar-toggler").click()
        panel = page.locator("#mobile-navigation")
        assert panel.get_attribute("class") is not None
        panel.wait_for(state="visible")
        page.wait_for_timeout(500)
        panel_box = panel.bounding_box()
        assert panel_box is not None
        assert 65 <= panel_box["x"] <= 75
        assert panel_box["x"] + panel_box["width"] >= 389
        panel_z_index = int(
            panel.evaluate("element => getComputedStyle(element).zIndex")
        )
        topbar_z_index = int(
            page.locator(".app-topbar").evaluate(
                "element => getComputedStyle(element).zIndex"
            )
        )
        backdrop_z_index = int(
            page.locator(".offcanvas-backdrop").evaluate(
                "element => getComputedStyle(element).zIndex"
            )
        )
        assert panel_z_index > topbar_z_index
        assert backdrop_z_index > topbar_z_index
        assert (
            panel.locator(".sidebar-profile-copy")
            .get_by_text("مدير تجربة الواجهة")
            .is_visible()
        )
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if capture_screenshots:
            page.screenshot(
                path=str(screenshot_directory / "mobile-arabic-sidebar.png"),
                full_page=False,
            )

        panel.locator('a[href="/accounts/me/"]').click()
        page.wait_for_load_state("networkidle")
        page.locator("#id_avatar").set_input_files(
            {
                "name": "avatar.png",
                "mimeType": "image/png",
                "buffer": _png_bytes(),
            }
        )
        assert page.locator("#avatar-preview").is_visible()
        page.locator('form[action="/accounts/me/avatar/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("#avatar-preview").is_visible()
        assert "/avatar/" in (
            page.locator("#avatar-preview").get_attribute("src") or ""
        )

        page.select_option("#language-select", "en")
        page.locator(".language-submit").click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("dir") == "ltr"
        assert page.get_by_role("heading", name="My profile").is_visible()
        mobile.close()

        desktop = browser.new_context(
            locale="en-US",
            viewport={"width": 1440, "height": 900},
        )
        desktop.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        desktop_page = desktop.new_page()
        desktop_page.goto(
            f"{live_server.url}/projects/{project.pk}/",
            wait_until="networkidle",
        )

        assert desktop_page.locator("html").get_attribute("dir") == "ltr"
        assert desktop_page.locator("#desktop-navigation").is_visible()
        assert desktop_page.locator(".app-footer").is_visible()
        assert (
            desktop_page.locator(".progress-ring-number")
            .get_by_text("50.00%")
            .is_visible()
        )
        assert (
            desktop_page.locator(".progress-ring-value").get_attribute(
                "stroke-dasharray"
            )
            == "50.00 100"
        )
        if capture_screenshots:
            desktop_page.screenshot(
                path=str(screenshot_directory / "desktop-english-project.png"),
                full_page=True,
            )
        desktop_page.locator("#sidebar-toggle").click()
        assert desktop_page.locator("body").evaluate(
            "element => element.classList.contains('sidebar-collapsed')"
        )
        assert desktop_page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        )
        desktop_page.goto(f"{live_server.url}/", wait_until="networkidle")
        assert "width: 50.00%" in (
            desktop_page.locator(".app-progress .progress-bar").first.get_attribute(
                "style"
            )
            or ""
        )

        desktop.close()
        browser.close()
