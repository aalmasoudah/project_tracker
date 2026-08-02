"""Arabic mobile external trainer submission workflow."""

import os
from datetime import UTC, date, datetime

import pytest
from django.contrib.auth.models import Group, Permission
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.attendance.models import AttendanceSubmission, Session
from apps.attendance.services import issue_trainer_link
from apps.courses.models import Course, CourseTrainerAssignment, Trainer
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.trainees.models import CourseEnrollment, Trainee


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_arabic_mobile_trainer_link_submission(live_server: LiveServer) -> None:
    department = Department.objects.create(
        code="BRW9", name_ar="الحضور", name_en="Attendance"
    )
    manager = User.objects.create_user(
        username="browser-phase9-manager",
        email="browser-phase9-manager@example.test",
        display_name="مدير الحضور",
        department=department,
        password="fictional-browser-password-9124",
        preferred_language="ar",
    )
    group = Group.objects.get_or_create(name="project_manager")[0]
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="attendance",
            codename__in=(
                "issue_trainer_link",
                "manage_managed_sessions",
                "view_session",
            ),
        )
    )
    manager.groups.add(group)
    supervisor = User.objects.create_user(
        username="browser-phase9-supervisor",
        email="browser-phase9-supervisor@example.test",
        display_name="مشرف الحضور",
        department=department,
        password="fictional-browser-password-9125",
    )
    project = Project.objects.create(
        code="PRJ-BRW9",
        name_ar="مشروع الحضور",
        name_en="Attendance Project",
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
    course = Course.objects.create(
        code="CRS-BRW9",
        project=project,
        name_ar="دورة الحضور",
        name_en="Attendance Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=5,
        start_at=datetime(2026, 8, 2, 9, tzinfo=UTC),
        end_at=datetime(2026, 9, 30, 16, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )
    trainer = Trainer.objects.create(
        code="TRN-BRW9",
        name_ar="مدرب خيالي",
        name_en="Fictional Trainer",
        email="browser-trainer@example.test",
        created_by=manager,
        updated_by=manager,
    )
    CourseTrainerAssignment.objects.create(
        course=course, trainer=trainer, assigned_by=manager
    )
    trainee = Trainee.objects.create(
        full_name="متدرب خيالي",
        phone="0500000091",
        created_by=manager,
        updated_by=manager,
    )
    CourseEnrollment.objects.create(
        course=course, trainee=trainee, trainee_number=1, created_by=manager
    )
    session = Session.objects.create(
        course=course,
        trainer=trainer,
        title_ar="جلسة خيالية",
        title_en="Fictional Session",
        start_at=datetime(2026, 8, 5, 9, tzinfo=UTC),
        end_at=datetime(2026, 8, 5, 11, tzinfo=UTC),
        created_by=manager,
        updated_by=manager,
    )
    _link, token = issue_trainer_link(actor=manager, session=session, lifetime_hours=72)
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path, headless=True
        )
        page = browser.new_page(locale="ar-SA", viewport={"width": 390, "height": 844})
        page.goto(f"{live_server.url}/attendance/t/{token}/")
        assert page.locator("html").get_attribute("dir") == "rtl"
        assert "متدرب خيالي" in page.content()
        page.locator("input[type=radio]").first.check()
        page.get_by_role("button", name="إرسال الحضور").click()
        page.wait_for_load_state("networkidle")
        assert "تم إرسال الحضور" in page.content()
        browser.close()
    assert AttendanceSubmission.objects.get().state == "pending_review"
