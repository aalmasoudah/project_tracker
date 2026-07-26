"""Phase 3 project, team, permission, and archive integration tests."""

from datetime import date
from decimal import Decimal
from typing import TypedDict

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client as WebClient
from django.urls import reverse

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.selectors import audit_events_visible_to
from apps.organizations.models import Department
from apps.projects.forms import ProjectForm
from apps.projects.models import Category, Client, Project, ProjectMembership
from apps.projects.selectors import projects_visible_to
from apps.projects.services import (
    archive_project,
    create_project,
    replace_project_team,
    save_reference,
    set_reference_archived,
    update_project,
)


class ProjectData(TypedDict):
    code: str
    name_ar: str
    name_en: str
    department: Department
    client: Client | None
    category: Category | None
    manager: User
    supervisor: User | None
    status: str
    priority: str
    start_date: date
    end_date: date
    budget: Decimal | None
    goals: str
    requirements: str
    notes: str


def role_user(
    *,
    username: str,
    role: str,
    department: Department,
) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase3-password-4821",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def project_data(
    *,
    code: str,
    department: Department,
    manager: User,
    supervisor: User | None = None,
) -> ProjectData:
    return {
        "code": code,
        "name_ar": "مشروع التحول",
        "name_en": "Transformation Project",
        "department": department,
        "client": None,
        "category": None,
        "manager": manager,
        "supervisor": supervisor,
        "status": Project.Status.DRAFT,
        "priority": Project.Priority.HIGH,
        "start_date": date(2026, 8, 1),
        "end_date": date(2026, 12, 31),
        "budget": Decimal("125000.00"),
        "goals": "رفع الكفاءة\nImprove efficiency",
        "requirements": "",
        "notes": "",
    }


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_role_scoped_project_visibility_and_budget_privacy() -> None:
    engineering = Department.objects.create(
        code="ENG",
        name_ar="الهندسة",
        name_en="Engineering",
    )
    finance = Department.objects.create(
        code="FIN",
        name_ar="المالية",
        name_en="Finance",
    )
    manager = role_user(
        username="eng-manager",
        role="project_manager",
        department=engineering,
    )
    other_manager = role_user(
        username="fin-manager",
        role="project_manager",
        department=finance,
    )
    supervisor = role_user(
        username="eng-supervisor",
        role="supervisor",
        department=engineering,
    )
    employee = role_user(
        username="eng-employee",
        role="employee",
        department=engineering,
    )
    outsider = role_user(
        username="fin-employee",
        role="employee",
        department=finance,
    )
    ceo = role_user(username="chief", role="ceo", department=engineering)

    managed_data = project_data(
        code="PRJ-100",
        department=engineering,
        manager=manager,
        supervisor=supervisor,
    )
    managed_data["status"] = Project.Status.ACTIVE
    managed = Project.objects.create(
        **managed_data,
        created_by=manager,
        updated_by=manager,
    )
    other = Project.objects.create(
        **project_data(
            code="PRJ-200",
            department=finance,
            manager=other_manager,
        ),
        created_by=other_manager,
        updated_by=other_manager,
    )
    ProjectMembership.objects.create(
        project=managed,
        user=employee,
        added_by=manager,
    )

    assert set(projects_visible_to(manager)) == {managed}
    assert set(projects_visible_to(supervisor)) == {managed}
    assert set(projects_visible_to(employee)) == {managed}
    assert not projects_visible_to(outsider).exists()
    assert set(projects_visible_to(ceo)) == {managed, other}

    web_client = WebClient()
    web_client.force_login(outsider)
    response = web_client.get(reverse("projects:detail", args=(managed.pk,)))
    assert response.status_code == 404

    web_client.force_login(supervisor)
    response = web_client.get(reverse("projects:detail", args=(managed.pk,)))
    assert response.status_code == 200
    assert b"SAR" not in response.content
    assert b"Budget" not in response.content

    web_client.force_login(manager)
    response = web_client.get(reverse("projects:detail", args=(managed.pk,)))
    assert b"SAR" in response.content


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_project_lifecycle_team_history_and_archived_read_only() -> None:
    department = Department.objects.create(
        code="OPS",
        name_ar="العمليات",
        name_en="Operations",
    )
    manager = role_user(
        username="ops-manager",
        role="project_manager",
        department=department,
    )
    employee = role_user(
        username="ops-employee",
        role="employee",
        department=department,
    )
    project = create_project(
        actor=manager,
        **project_data(
            code="OPS-101",
            department=department,
            manager=manager,
        ),
    )
    assert AuditEvent.objects.filter(
        scope=AuditEvent.Scope.PROJECTS,
        action=actions.PROJECT_CREATED,
        target_id=str(project.pk),
    ).exists()

    replace_project_team(actor=manager, project=project, members=[employee])
    membership = ProjectMembership.objects.get(project=project, user=employee)
    assert membership.removed_at is None

    replace_project_team(actor=manager, project=project, members=[])
    assert ProjectMembership.objects.filter(
        pk=membership.pk,
        removed_at__isnull=False,
        removed_by=manager,
    ).exists()
    assert (
        AuditEvent.objects.filter(
            action=actions.PROJECT_TEAM_UPDATED,
            target_id=str(project.pk),
        ).count()
        == 2
    )
    with pytest.raises(PermissionDenied):
        ProjectMembership.objects.filter(pk=membership.pk).delete()

    changed = project_data(
        code=project.code,
        department=department,
        manager=manager,
    )
    changed["status"] = Project.Status.ACTIVE
    project = update_project(actor=manager, project=project, **changed)
    assert project.status == Project.Status.ACTIVE

    changed["status"] = Project.Status.DRAFT
    with pytest.raises(ValidationError):
        update_project(actor=manager, project=project, **changed)

    project = archive_project(actor=manager, project=project)
    assert project.is_archived
    with pytest.raises(PermissionDenied):
        Project.objects.filter(pk=project.pk).delete()
    with pytest.raises(PermissionDenied):
        update_project(actor=manager, project=project, **changed)

    technical_admin = role_user(
        username="technical-auditor",
        role="technical_admin",
        department=department,
    )
    assert (
        not audit_events_visible_to(technical_admin)
        .filter(scope=AuditEvent.Scope.PROJECTS)
        .exists()
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_reference_archiving_is_audited_and_blocked_while_in_use() -> None:
    department = Department.objects.create(
        code="PMO",
        name_ar="إدارة المشاريع",
        name_en="Project Office",
    )
    executive = role_user(
        username="executive",
        role="executive_manager",
        department=department,
    )
    manager = role_user(
        username="pmo-manager",
        role="project_manager",
        department=department,
    )
    client = save_reference(
        actor=executive,
        model=Client,
        code="cl-01",
        name_ar="العميل الأول",
        name_en="First Client",
    )
    category = save_reference(
        actor=executive,
        model=Category,
        code="digital",
        name_ar="رقمي",
        name_en="Digital",
    )
    assert isinstance(client, Client)
    assert isinstance(category, Category)
    data = project_data(code="PMO-101", department=department, manager=manager)
    data["client"] = client
    data["category"] = category
    project = create_project(actor=manager, **data)

    with pytest.raises(ValidationError):
        set_reference_archived(
            actor=executive,
            reference=client,
            archived=True,
        )

    archive_project(actor=manager, project=project)
    set_reference_archived(actor=executive, reference=client, archived=True)
    client.refresh_from_db()
    assert client.is_archived
    assert AuditEvent.objects.filter(
        action=actions.CLIENT_ARCHIVED,
        target_id=str(client.pk),
    ).exists()

    with pytest.raises(ValidationError):
        save_reference(
            actor=executive,
            model=Client,
            code=client.code,
            name_ar=client.name_ar,
            name_en="Changed",
            instance=client,
        )


@pytest.mark.integration
@pytest.mark.django_db
def test_project_form_rejects_invalid_dates_and_budget_precision() -> None:
    department = Department.objects.create(
        code="QA",
        name_ar="الجودة",
        name_en="Quality",
    )
    manager = role_user(
        username="qa-manager",
        role="project_manager",
        department=department,
    )
    data = dict(
        project_data(
            code="QA-101",
            department=department,
            manager=manager,
        )
    )
    data.update(
        {
            "department": str(department.pk),
            "manager": str(manager.pk),
            "start_date": "2026-09-02",
            "end_date": "2026-09-01",
            "budget": "12.345",
        }
    )
    form = ProjectForm(data=data, actor=manager)

    assert not form.is_valid()
    assert "end_date" in form.errors
    assert "budget" in form.errors
