"""Arabic rejection lifecycle and English approved-correction browser coverage."""

import os

import pytest
from django.contrib.auth.models import Group, Permission
from playwright.sync_api import Page, sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.attendance.models import AttendanceEntry, AttendanceSubmission
from apps.attendance.services import issue_trainer_link, submit_attendance
from tests.integration.test_phase9_attendance import (
    create_one_session,
    setup_course,
)

PASSWORD = "fictional-phase9-password-4926"


def sign_in(page: Page, base_url: str, username: str) -> None:
    page.goto(f"{base_url}/accounts/login/")
    page.locator('input[name="username"]').fill(username)
    page.locator('input[name="password"]').fill(PASSWORD)
    page.locator(".auth-card button[type=submit]").click()
    page.wait_for_load_state("networkidle")


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_phase10_reject_reopen_approve_and_correct(
    live_server: LiveServer,
) -> None:
    manager_group = Group.objects.get_or_create(name="project_manager")[0]
    manager_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="trainees",
            codename="add_courseenrollment",
        ),
        *Permission.objects.filter(
            content_type__app_label="attendance",
            codename__in=(
                "correct_managed_attendance",
                "issue_trainer_link",
                "manage_managed_sessions",
                "view_attendanceentry",
                "view_attendancesubmission",
                "view_managed_attendance",
                "view_session",
            ),
        ),
    )
    supervisor_group = Group.objects.get_or_create(name="supervisor")[0]
    supervisor_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="attendance",
            codename__in=(
                "review_attendance",
                "view_attendanceentry",
                "view_attendancesubmission",
                "view_context_sessions",
                "view_session",
                "view_supervised_attendance",
            ),
        )
    )
    manager, supervisor, course, trainer = setup_course()
    manager.preferred_language = "en"
    manager.save(update_fields=("preferred_language",))
    session = create_one_session(manager, course, trainer)
    link, token = issue_trainer_link(actor=manager, session=session, lifetime_hours=72)
    submission = submit_attendance(
        link=link,
        entries={
            participant.pk: (AttendanceEntry.Value.PRESENT, "")
            for participant in session.participants.all()
        },
        trainer_notes="إرسال تجريبي",
        evidence_files=[],
    )
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path, headless=True
        )
        context = browser.new_context(
            locale="ar-SA", viewport={"width": 390, "height": 844}
        )
        page = context.new_page()
        sign_in(page, live_server.url, supervisor.username)
        page.goto(f"{live_server.url}/attendance/review/{submission.pk}/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.locator('textarea[name="reason"]').fill("تصحيح سجل الحضور")
        page.locator('form[action$="/reject/"] button').click()
        page.wait_for_load_state("networkidle")

        page.goto(f"{live_server.url}/attendance/t/{token}/")
        assert "تصحيح سجل الحضور" in page.content()
        page.locator('input[value="late"]').first.check()
        page.get_by_role("button", name="إرسال الحضور").click()
        page.wait_for_load_state("networkidle")
        assert "تم إرسال الحضور" in page.content()

        page.goto(f"{live_server.url}/attendance/review/{submission.pk}/")
        page.locator('form[action$="/approve/"] button').click()
        page.wait_for_load_state("networkidle")
        page.goto(f"{live_server.url}/attendance/t/{token}/")
        assert page.locator('input[type="radio"]').count() == 0

        context.clear_cookies()
        sign_in(page, live_server.url, manager.username)
        page.goto(f"{live_server.url}/attendance/review/{submission.pk}/correct/")
        assert page.locator("html").get_attribute("dir") == "ltr"
        page.locator('input[value="excused"]').first.check()
        page.locator('textarea[name="reason"]').fill("Verified register correction")
        page.get_by_role("button", name="Save correction").click()
        page.wait_for_load_state("networkidle")
        assert "Attendance corrected without reapproval." in page.content()
        browser.close()
    assert AttendanceSubmission.objects.get(pk=submission.pk).state == "approved"
