"""Phase 6 progress integration, authorization, and privacy tests."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse
from pytest_django import DjangoAssertNumQueries

from apps.accounts.models import User
from apps.courses.models import Course
from apps.organizations.models import Department
from apps.progress.calculations import ProgressState
from apps.progress.services import (
    course_progress_for,
    project_progress_for,
    task_progress_for,
)
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskAssignment


def make_user(
    username: str,
    role: str,
    department: Department,
) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase6-password-7531",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def make_project(
    *,
    code: str,
    manager: User,
    department: Department,
    supervisor: User | None = None,
) -> Project:
    return Project.objects.create(
        code=code,
        name_ar="مشروع التقدم",
        name_en="Progress Project",
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


def make_course(
    *,
    code: str,
    project: Project,
    actor: User,
    status: str = Course.Status.ACTIVE,
) -> Course:
    return Course.objects.create(
        code=code,
        project=project,
        name_ar=f"دورة {code}",
        name_en=f"Course {code}",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=20,
        start_at=datetime(2026, 9, 1, 8, tzinfo=UTC),
        end_at=datetime(2026, 9, 1, 16, tzinfo=UTC),
        status=status,
        created_by=actor,
        updated_by=actor,
    )


def make_task(
    *,
    code: str,
    actor: User,
    status: str,
    project: Project | None = None,
    course: Course | None = None,
    parent: Task | None = None,
) -> Task:
    return Task.objects.create(
        code=code,
        project=project,
        course=course,
        parent=parent,
        name_ar=f"مهمة {code}",
        name_en=f"Task {code}",
        status=status,
        priority=Task.Priority.MEDIUM,
        created_by=actor,
        updated_by=actor,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_task_course_and_equal_category_project_formulas(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    department = Department.objects.create(
        code="PRG6", name_ar="إدارة التقدم", name_en="Progress"
    )
    manager = make_user("progress-manager", "project_manager", department)
    project = make_project(code="PRJ-P61", manager=manager, department=department)
    direct_parent = make_task(
        code="TSK-P61",
        actor=manager,
        project=project,
        status=Task.Status.COMPLETED,
    )
    make_task(
        code="TSK-P62",
        actor=manager,
        project=project,
        parent=direct_parent,
        status=Task.Status.COMPLETED,
    )
    make_task(
        code="TSK-P63",
        actor=manager,
        project=project,
        parent=direct_parent,
        status=Task.Status.TODO,
    )
    make_task(
        code="TSK-P64",
        actor=manager,
        project=project,
        status=Task.Status.CANCELLED,
    )
    course = make_course(code="CRS-P61", project=project, actor=manager)
    make_task(
        code="TSK-P65",
        actor=manager,
        course=course,
        status=Task.Status.COMPLETED,
    )

    manager.get_all_permissions()
    task_result = task_progress_for(manager, direct_parent)
    course_result = course_progress_for(manager, course)
    assert task_result is not None
    assert course_result is not None
    assert task_result.percentage == Decimal("50.00")
    assert course_result.percentage == Decimal("100.00")
    with django_assert_num_queries(4):
        project_result = project_progress_for(manager, project)

    assert project_result is not None
    assert project_result.state == ProgressState.VALUE
    assert project_result.percentage == Decimal("75.00")


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_progress_visibility_and_empty_or_excluded_states() -> None:
    department = Department.objects.create(
        code="SEC6", name_ar="إدارة الأمن", name_en="Security"
    )
    manager = make_user("phase6-manager", "project_manager", department)
    supervisor = make_user("phase6-supervisor", "supervisor", department)
    unrelated_supervisor = make_user(
        "phase6-unrelated-supervisor",
        "supervisor",
        department,
    )
    employee = make_user("phase6-employee", "employee", department)
    executive = make_user("phase6-executive", "executive_manager", department)
    project = make_project(
        code="PRJ-P62",
        manager=manager,
        supervisor=supervisor,
        department=department,
    )
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    course = make_course(code="CRS-P62", project=project, actor=manager)
    task = make_task(
        code="TSK-P66",
        actor=manager,
        course=course,
        status=Task.Status.TODO,
    )
    TaskAssignment.objects.create(
        task=task,
        user=employee,
        is_primary=True,
        assigned_by=manager,
    )

    assert project_progress_for(manager, project) is not None
    assert project_progress_for(supervisor, project) is not None
    assert project_progress_for(executive, project) is not None
    assert course_progress_for(supervisor, course) is not None
    assert task_progress_for(supervisor, task) is not None
    assert project_progress_for(unrelated_supervisor, project) is None
    assert course_progress_for(unrelated_supervisor, course) is None
    assert task_progress_for(unrelated_supervisor, task) is None
    assert project_progress_for(employee, project) is None
    assert course_progress_for(employee, course) is None
    assert task_progress_for(employee, task) is None

    draft_course = make_course(
        code="CRS-P63",
        project=project,
        actor=manager,
        status=Course.Status.DRAFT,
    )
    assert project_progress_for(supervisor, project) is None
    assert project_progress_for(manager, project) is not None

    empty_project = make_project(
        code="PRJ-P63",
        manager=manager,
        department=department,
    )
    empty_result = project_progress_for(manager, empty_project)
    assert empty_result is not None
    assert empty_result.state == ProgressState.EMPTY
    assert empty_result.percentage == Decimal("0.00")

    draft_course.status = Course.Status.CANCELLED
    draft_course.save(update_fields=("status", "updated_at"))
    excluded_course = course_progress_for(manager, draft_course)
    assert excluded_course is not None
    assert excluded_course.state == ProgressState.EXCLUDED

    empty_project.status = Project.Status.CANCELLED
    empty_project.save(update_fields=("status", "updated_at"))
    excluded_project = project_progress_for(manager, empty_project)
    assert excluded_project is not None
    assert excluded_project.state == ProgressState.EXCLUDED


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_assignee_detail_hides_progress_and_unapproved_hierarchy_names() -> None:
    department = Department.objects.create(
        code="PRI6", name_ar="إدارة الخصوصية", name_en="Privacy"
    )
    manager = make_user("privacy-manager", "project_manager", department)
    employee = make_user("privacy-employee", "employee", department)
    project = make_project(code="PRJ-P64", manager=manager, department=department)
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    hidden_parent = make_task(
        code="TSK-HIDDEN-PARENT",
        actor=manager,
        project=project,
        status=Task.Status.COMPLETED,
    )
    visible_child = make_task(
        code="TSK-VISIBLE-CHILD",
        actor=manager,
        project=project,
        parent=hidden_parent,
        status=Task.Status.TODO,
    )
    visible_parent = make_task(
        code="TSK-VISIBLE-PARENT",
        actor=manager,
        project=project,
        status=Task.Status.TODO,
    )
    hidden_child = make_task(
        code="TSK-HIDDEN-CHILD",
        actor=manager,
        project=project,
        parent=visible_parent,
        status=Task.Status.COMPLETED,
    )
    for task in (visible_child, visible_parent):
        TaskAssignment.objects.create(
            task=task,
            user=employee,
            is_primary=True,
            assigned_by=manager,
        )

    client = Client()
    client.force_login(employee)
    child_response = client.get(reverse("tasks:detail", args=(visible_child.pk,)))
    parent_response = client.get(reverse("tasks:detail", args=(visible_parent.pk,)))

    assert child_response.status_code == 200
    assert parent_response.status_code == 200
    child_html = child_response.content.decode()
    parent_html = parent_response.content.decode()
    assert "TSK-HIDDEN-PARENT" not in child_html
    assert "TSK-HIDDEN-CHILD" not in parent_html
    assert "Progress" not in child_html
    assert "Progress" not in parent_html
    assert (
        client.get(reverse("tasks:detail", args=(hidden_parent.pk,))).status_code == 404
    )
    assert (
        client.get(reverse("tasks:detail", args=(hidden_child.pk,))).status_code == 404
    )
