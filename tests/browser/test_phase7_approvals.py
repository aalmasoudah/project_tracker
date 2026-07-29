"""Critical Arabic mobile Phase 7 milestone approval workflow."""

import os
from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import Client
from playwright.sync_api import BrowserContext, sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.approvals.models import ApprovalDecision, ApprovalRequest, Milestone
from apps.organizations.models import Department
from apps.projects.models import Project


def add_session_cookie(
    context: BrowserContext,
    *,
    cookie_value: str,
    live_server: LiveServer,
) -> None:
    context.add_cookies(
        [
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": cookie_value,
                "url": live_server.url,
            }
        ]
    )


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_milestone_two_step_approval(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="BRW7",
        name_ar="إدارة الموافقات",
        name_en="Approvals",
    )
    manager = User.objects.create_user(
        username="browser-phase7-manager",
        email="browser-phase7-manager@example.test",
        display_name="مدير المشروع",
        department=department,
        password="fictional-browser-password-7124",
    )
    supervisor = User.objects.create_user(
        username="browser-phase7-supervisor",
        email="browser-phase7-supervisor@example.test",
        display_name="مشرف المشروع",
        department=department,
        password="fictional-browser-password-7125",
    )
    manager_group = Group.objects.get_or_create(name="project_manager")[0]
    manager_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="approvals",
            codename__in=(
                "add_milestone",
                "archive_milestone",
                "change_milestone",
                "decide_manager_approval",
                "restore_milestone",
                "submit_approval",
                "view_approvalrequest",
                "view_managed_approvals",
                "view_managed_milestones",
                "view_milestone",
            ),
        )
    )
    manager.groups.add(manager_group)
    supervisor_group = Group.objects.get_or_create(name="supervisor")[0]
    supervisor_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="approvals",
            codename__in=(
                "decide_supervisor_approval",
                "view_approvalrequest",
                "view_context_approvals",
                "view_context_milestones",
                "view_milestone",
            ),
        )
    )
    supervisor.groups.add(supervisor_group)
    project = Project.objects.create(
        code="PRJ-BRW7",
        name_ar="مشروع الموافقات",
        name_en="Approval Project",
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
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None
    manager_client = Client()
    manager_client.force_login(manager)
    manager_cookie = manager_client.cookies[settings.SESSION_COOKIE_NAME].value
    supervisor_client = Client()
    supervisor_client.force_login(supervisor)
    supervisor_cookie = supervisor_client.cookies[settings.SESSION_COOKIE_NAME].value

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path,
            headless=True,
        )
        manager_context = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        add_session_cookie(
            manager_context,
            cookie_value=manager_cookie,
            live_server=live_server,
        )
        manager_page = manager_context.new_page()
        manager_page.goto(
            f"{live_server.url}/approvals/milestones/create/",
            wait_until="networkidle",
        )
        assert manager_page.locator("html").get_attribute("dir") == "rtl"
        manager_page.locator("#id_code").fill("mls-brw7")
        manager_page.locator("#id_project").select_option(str(project.pk))
        manager_page.locator("#id_name_ar").fill("جاهزية الإطلاق")
        manager_page.locator("#id_name_en").fill("Launch Readiness")
        manager_page.locator("#id_description").fill(
            "التحقق من جاهزية الإطلاق التجريبي."
        )
        manager_page.locator("#id_start_date").fill("2026-08-10")
        manager_page.locator("#id_due_date").fill("2026-09-01")
        manager_page.get_by_role("button", name="حفظ").click()
        manager_page.wait_for_load_state("networkidle")
        assert manager_page.get_by_role(
            "heading",
            name="جاهزية الإطلاق",
        ).is_visible()
        milestone_url = manager_page.url

        manager_page.get_by_role("link", name="تعديل").click()
        manager_page.locator("#id_status").select_option(Milestone.Status.IN_PROGRESS)
        manager_page.get_by_role("button", name="حفظ").click()
        manager_page.get_by_role("link", name="إرسال للموافقة").click()
        manager_page.get_by_role("button", name="تأكيد الإرسال").click()
        manager_page.wait_for_load_state("networkidle")
        approval_url = manager_page.url
        assert manager_page.get_by_text(
            "بانتظار المشرف",
            exact=True,
        ).is_visible()

        supervisor_context = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        add_session_cookie(
            supervisor_context,
            cookie_value=supervisor_cookie,
            live_server=live_server,
        )
        supervisor_page = supervisor_context.new_page()
        supervisor_page.goto(approval_url, wait_until="networkidle")
        supervisor_page.get_by_role("button", name="موافقة").click()
        supervisor_page.wait_for_load_state("networkidle")
        assert supervisor_page.get_by_text(
            "بانتظار مدير المشروع",
            exact=True,
        ).is_visible()
        assert supervisor_page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        )

        manager_page.goto(approval_url, wait_until="networkidle")
        manager_page.get_by_role("button", name="موافقة").click()
        manager_page.wait_for_load_state("networkidle")
        assert manager_page.get_by_text("تمت الموافقة", exact=True).is_visible()

        manager_page.goto(
            milestone_url,
            wait_until="networkidle",
        )
        assert manager_page.get_by_text("100,00%", exact=True).is_visible()
        assert manager_page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        )
        manager_page.locator(".navbar-toggler").click()
        manager_page.locator("#language-select").select_option("en")
        manager_page.locator('form[action="/i18n/setlang/"] button').click()
        manager_page.wait_for_load_state("networkidle")
        assert manager_page.locator("html").get_attribute("dir") == "ltr"
        assert manager_page.get_by_text("Completed", exact=True).is_visible()
        assert manager_page.get_by_text("100.00%", exact=True).is_visible()

        supervisor_context.close()
        manager_context.close()
        browser.close()

    milestone = Milestone.objects.get(code="MLS-BRW7")
    approval_request = ApprovalRequest.objects.get(milestone=milestone)
    assert approval_request.status == ApprovalRequest.Status.APPROVED
    assert ApprovalDecision.objects.filter(step__request=approval_request).count() == 2
