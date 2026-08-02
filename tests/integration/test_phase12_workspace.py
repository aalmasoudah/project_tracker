"""Phase 12 dashboard, search, saved-filter, and planning security tests."""

from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.workspace.models import SavedFilter
from apps.workspace.services import global_search


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase12-password-7124",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def project(
    code: str,
    manager: User,
    department: Department,
    *,
    name_ar: str = "مشروع التحول الرقمي",
) -> Project:
    return Project.objects.create(
        code=code,
        name_ar=name_ar,
        name_en="Digital transformation",
        department=department,
        manager=manager,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 9, 30),
        created_by=manager,
        updated_by=manager,
    )


def task(code: str, owner: Project, actor: User, name_ar: str) -> Task:
    return Task.objects.create(
        code=code,
        project=owner,
        name_ar=name_ar,
        name_en=f"Task {code}",
        status=Task.Status.TODO,
        priority=Task.Priority.MEDIUM,
        start_date=date(2026, 8, 10),
        due_date=date(2026, 8, 20),
        created_by=actor,
        updated_by=actor,
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_dashboard_search_and_kanban_do_not_leak_other_manager_scope() -> None:
    department = Department.objects.create(
        code="WS12", name_ar="إدارة المشاريع", name_en="Projects"
    )
    manager = role_user("workspace-manager", "project_manager", department)
    outsider = role_user("workspace-outsider", "project_manager", department)
    visible_project = project("WS-VISIBLE", manager, department)
    hidden_project = project("WS-HIDDEN", outsider, department)
    visible_task = task("WS-TASK-V", visible_project, manager, "مهمة التحول")
    hidden_task = task("WS-TASK-H", hidden_project, outsider, "مهمة التحول السرية")
    client = Client()
    client.force_login(manager)

    dashboard = client.get(reverse("home"))
    search = client.get(reverse("workspace:search"), {"q": "التحول"})
    board = client.get(reverse("workspace:kanban"), {"q": "التحول"})

    assert dashboard.status_code == 200
    assert visible_task.code in dashboard.content.decode()
    assert hidden_task.code not in dashboard.content.decode()
    assert visible_project.code in search.content.decode()
    assert hidden_project.code not in search.content.decode()
    assert visible_task.code in board.content.decode()
    assert hidden_task.code not in board.content.decode()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_saved_filters_are_private_allowlisted_and_owner_deletable() -> None:
    department = Department.objects.create(
        code="SF12", name_ar="إدارة المرشحات", name_en="Filters"
    )
    owner = role_user("filter-owner", "employee", department)
    other = role_user("filter-other", "employee", department)
    client = Client()
    client.force_login(owner)

    created = client.post(
        reverse("workspace:filter_save"),
        {
            "name": "My calendar",
            "view_type": "calendar",
            "q": "مهمة",
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
        },
    )
    saved_filter = SavedFilter.objects.get(owner=owner)
    assert created.status_code == 302
    assert saved_filter.criteria == {
        "q": "مهمة",
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
    }
    duplicate = client.post(
        reverse("workspace:filter_save"),
        {
            "name": "my CALENDAR",
            "view_type": "calendar",
            "q": "مهمة",
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
        },
    )
    assert duplicate.status_code == 302
    assert SavedFilter.objects.filter(owner=owner).count() == 1

    forged = client.post(
        reverse("workspace:filter_save"),
        {
            "name": "Forged",
            "view_type": "admin",
            "q": "secret",
            "next": "https://attacker.example/collect",
        },
    )
    assert forged.status_code == 302
    assert forged["Location"] == reverse("workspace:filters")
    assert not SavedFilter.objects.filter(name="Forged").exists()

    client.force_login(other)
    assert (
        client.get(reverse("workspace:filter_use", args=(saved_filter.pk,))).status_code
        == 404
    )
    assert (
        client.post(
            reverse("workspace:filter_delete", args=(saved_filter.pk,))
        ).status_code
        == 404
    )
    assert SavedFilter.objects.filter(pk=saved_filter.pk).exists()

    client.force_login(owner)
    assert (
        client.post(
            reverse("workspace:filter_delete", args=(saved_filter.pk,))
        ).status_code
        == 302
    )
    assert not SavedFilter.objects.filter(pk=saved_filter.pk).exists()


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    (
        "technical_admin",
        "ceo",
        "executive_manager",
        "project_manager",
        "supervisor",
        "employee",
        "contractor",
    ),
)
def test_every_approved_role_receives_its_dashboard_context(role: str) -> None:
    department = Department.objects.create(
        code=f"R{role[:5].upper()}",
        name_ar=f"إدارة {role}",
        name_en=f"{role} department",
    )
    actor = role_user(f"dashboard-{role}", role, department)
    client = Client()
    client.force_login(actor)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response.context["dashboard_role"]


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_planning_views_are_read_only_and_reject_excessive_ranges() -> None:
    department = Department.objects.create(
        code="PL12", name_ar="إدارة التخطيط", name_en="Planning"
    )
    manager = role_user("planning-manager", "project_manager", department)
    client = Client()
    client.force_login(manager)

    for route in ("workspace:calendar", "workspace:timeline", "workspace:gantt"):
        response = client.get(
            reverse(route),
            {"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )
        assert response.status_code == 200
        assert response.context["form"].errors
        assert response.context["items"] == ()
        assert client.post(reverse(route)).status_code == 405


@pytest.mark.integration
@pytest.mark.django_db
def test_global_search_query_count_is_bounded_with_volume() -> None:
    department = Department.objects.create(
        code="PF12", name_ar="إدارة الأداء", name_en="Performance"
    )
    manager = role_user("query-manager", "project_manager", department)
    for number in range(35):
        project(f"QRY-{number:02}", manager, department)

    with CaptureQueriesContext(connection) as captured:
        sections = global_search(manager, "Digital")
        assert sum(section.total for section in sections) == 35

    assert len(captured) <= 12
