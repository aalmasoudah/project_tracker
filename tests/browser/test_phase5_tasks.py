"""Critical Arabic mobile browser workflow for Phase 5."""

import os
from datetime import date

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import Client
from playwright.sync_api import sync_playwright
from pytest_django.live_server_helper import LiveServer

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskComment


@pytest.mark.browser
@pytest.mark.django_db(transaction=True)
def test_mobile_arabic_task_creation_and_assignee_workflow(
    live_server: LiveServer,
) -> None:
    department = Department.objects.create(
        code="TSK5",
        name_ar="إدارة تنفيذ المشاريع",
        name_en="Project Delivery",
    )
    manager = User.objects.create_user(
        username="browser-phase5-manager",
        email="browser-phase5-manager@example.test",
        display_name="مدير المشروع",
        department=department,
        password="fictional-browser-password-5391",
    )
    manager_group = Group.objects.get_or_create(name="project_manager")[0]
    manager_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="tasks",
            codename__in=(
                "add_task",
                "change_task",
                "comment_task",
                "manage_task_assignments",
                "upload_task_file",
                "view_managed_tasks",
                "view_task",
            ),
        )
    )
    manager.groups.add(manager_group)
    employee = User.objects.create_user(
        username="browser-phase5-employee",
        email="browser-phase5-employee@example.test",
        display_name="منفذ المهمة",
        department=department,
        password="fictional-browser-password-5392",
    )
    employee_group = Group.objects.get_or_create(name="employee")[0]
    employee_group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="tasks",
            codename__in=(
                "comment_task",
                "update_assigned_task",
                "upload_task_file",
                "view_assigned_tasks",
                "view_task",
            ),
        )
    )
    employee.groups.add(employee_group)
    project = Project.objects.create(
        code="PRJ-TSK5",
        name_ar="مشروع البوابة الداخلية",
        name_en="Internal Portal Project",
        department=department,
        manager=manager,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=manager,
        updated_by=manager,
    )
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    manager_client = Client()
    manager_client.force_login(manager)
    manager_cookie = manager_client.cookies[settings.SESSION_COOKIE_NAME]
    employee_client = Client()
    employee_client.force_login(employee)
    employee_cookie = employee_client.cookies[settings.SESSION_COOKIE_NAME]
    executable_path = os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE") or None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=executable_path,
            headless=True,
        )
        manager_context = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        manager_context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": manager_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        page = manager_context.new_page()
        page.goto(f"{live_server.url}/tasks/create/", wait_until="networkidle")
        assert page.locator("html").get_attribute("dir") == "rtl"
        page.locator("#id_code").fill("tsk-rtl")
        page.locator("#id_project").select_option(str(project.pk))
        page.locator("#id_name_ar").fill("إعداد لوحة متابعة المشروع")
        page.locator("#id_name_en").fill("Prepare Project Dashboard")
        page.locator("#id_description").fill("تنفيذ الواجهة ومراجعة البيانات.")
        page.locator("#id_priority").select_option("high")
        page.locator("#id_start_date").fill("2026-08-10")
        page.locator("#id_due_date").fill("2026-08-20")
        page.locator("#id_estimated_hours").fill("12.50")
        page.locator("#id_assignees").select_option(str(employee.pk))
        page.locator("#id_primary_owner").select_option(str(employee.pk))
        page.get_by_role("button", name="حفظ").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_role(
            "heading", name="إعداد لوحة متابعة المشروع"
        ).is_visible()
        assert page.get_by_text("منفذ المهمة", exact=False).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        manager_context.close()

        employee_context = browser.new_context(
            locale="ar-SA",
            viewport={"width": 390, "height": 844},
        )
        employee_context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": employee_cookie.value,
                    "url": live_server.url,
                }
            ]
        )
        page = employee_context.new_page()
        page.goto(f"{live_server.url}/tasks/", wait_until="networkidle")
        page.get_by_role("link", name="إعداد لوحة متابعة المشروع").click()
        page.get_by_role("link", name="تحديث مهمتي").click()
        page.locator("#id_status").select_option(Task.Status.IN_PROGRESS)
        page.locator("#id_actual_hours").fill("3.25")
        page.get_by_role("button", name="حفظ").click()
        page.get_by_role("link", name="إضافة تعليق").click()
        page.locator("#id_body").fill("بدأ التنفيذ وتمت مراجعة المتطلبات.")
        page.get_by_role("button", name="إضافة تعليق").click()
        page.wait_for_load_state("networkidle")
        assert page.get_by_text("بدأ التنفيذ وتمت مراجعة المتطلبات.").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.locator("#language-select").select_option("en")
        page.locator('form[action="/i18n/setlang/"] button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.locator("html").get_attribute("dir") == "ltr"
        employee_context.close()
        browser.close()

    task = Task.objects.get(code="TSK-RTL")
    assert task.status == Task.Status.IN_PROGRESS
    assert task.actual_hours is not None
    assert TaskComment.objects.filter(
        task=task,
        author=employee,
        body="بدأ التنفيذ وتمت مراجعة المتطلبات.",
    ).exists()
