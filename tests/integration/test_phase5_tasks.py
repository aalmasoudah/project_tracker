"""Phase 5 task, collaboration, permission, and lifecycle tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as WebClient
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.courses.models import Course
from apps.courses.services import archive_course
from apps.organizations.models import Department
from apps.projects.models import Project, ProjectMembership
from apps.projects.services import archive_project
from apps.tasks.models import Task, TaskAssignment, TaskFile
from apps.tasks.selectors import tasks_visible_to
from apps.tasks.services import (
    add_task_comment,
    archive_task,
    create_task,
    replace_task_tags,
    restore_task,
    save_tag,
    update_assigned_task,
    upload_task_file,
)

PHASE5_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.tasks.migrations.0002_seed_phase5_permissions"
    ).ROLE_TASK_PERMISSIONS,
)


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase5-password-3618",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def make_project(
    *,
    code: str,
    department: Department,
    manager: User,
    supervisor: User | None = None,
) -> Project:
    return Project.objects.create(
        code=code,
        name_ar="مشروع التحول الرقمي",
        name_en="Digital Transformation Project",
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


def create_project_task(
    *,
    actor: User,
    project: Project,
    assignee: User,
    code: str,
    parent: Task | None = None,
    status: str = Task.Status.TODO,
    blocking_reason: str = "",
) -> Task:
    return create_task(
        actor=actor,
        assignees=[assignee],
        primary_owner=assignee,
        code=code,
        project=project,
        course=None,
        parent=parent,
        name_ar=f"مهمة {code}",
        name_en=f"Task {code}",
        description="A fictional task.",
        status=status,
        priority=Task.Priority.HIGH,
        start_date=date(2026, 8, 10),
        due_date=date(2026, 8, 20),
        estimated_hours=Decimal("8.00"),
        actual_hours=None,
        blocking_reason=blocking_reason,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_approved_phase5_matrix() -> None:
    for role_code, permission_keys in PHASE5_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="tasks"
            )
        }
        assert actual == permission_keys


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_task_visibility_and_direct_url_privacy() -> None:
    department = Department.objects.create(
        code="OPS5", name_ar="العمليات", name_en="Operations"
    )
    other_department = Department.objects.create(
        code="OUT5", name_ar="الخدمات", name_en="Services"
    )
    manager = role_user("task-manager", "project_manager", department)
    supervisor = role_user("task-supervisor", "supervisor", department)
    employee = role_user("task-employee", "employee", department)
    unassigned_member = role_user("task-member", "employee", department)
    outsider = role_user("task-outsider", "employee", other_department)
    executive = role_user("task-executive", "executive_manager", department)
    ceo = role_user("task-ceo", "ceo", department)
    technical_admin = role_user("task-admin", "technical_admin", department)
    project = make_project(
        code="PRJ-T01",
        department=department,
        manager=manager,
        supervisor=supervisor,
    )
    ProjectMembership.objects.create(project=project, user=employee, added_by=manager)
    ProjectMembership.objects.create(
        project=project, user=unassigned_member, added_by=manager
    )
    task = create_project_task(
        actor=manager,
        project=project,
        assignee=employee,
        code="TSK-101",
    )

    assert set(tasks_visible_to(manager)) == {task}
    assert set(tasks_visible_to(supervisor)) == {task}
    assert set(tasks_visible_to(employee)) == {task}
    assert set(tasks_visible_to(executive)) == {task}
    assert set(tasks_visible_to(ceo)) == {task}
    assert set(tasks_visible_to(employee, search="مهمة")) == {task}
    assert not tasks_visible_to(unassigned_member).exists()
    assert not tasks_visible_to(outsider).exists()
    assert not tasks_visible_to(technical_admin).exists()

    client = WebClient()
    client.force_login(employee)
    assert client.get(reverse("tasks:detail", args=(task.pk,))).status_code == 200
    client.force_login(unassigned_member)
    assert client.get(reverse("tasks:detail", args=(task.pk,))).status_code == 404
    client.force_login(technical_admin)
    assert client.get(reverse("tasks:list")).status_code == 403


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_hierarchy_collaboration_lifecycle_audit_and_archive_guards() -> None:
    department = Department.objects.create(
        code="PMO5", name_ar="مكتب المشاريع", name_en="PMO"
    )
    manager = role_user("phase5-manager", "project_manager", department)
    employee = role_user("phase5-employee", "employee", department)
    ProjectMembership.objects.create(
        project=(
            project := make_project(
                code="PRJ-T02", department=department, manager=manager
            )
        ),
        user=employee,
        added_by=manager,
    )
    root = create_project_task(
        actor=manager, project=project, assignee=employee, code="TSK-ROOT"
    )
    child = create_project_task(
        actor=manager,
        project=project,
        assignee=employee,
        code="TSK-CHILD",
        parent=root,
    )
    grandchild = create_project_task(
        actor=manager,
        project=project,
        assignee=employee,
        code="TSK-GRAND",
        parent=child,
    )
    with pytest.raises(ValidationError):
        create_project_task(
            actor=manager,
            project=project,
            assignee=employee,
            code="TSK-TOO-DEEP",
            parent=grandchild,
        )

    root.parent = grandchild
    with pytest.raises(ValidationError):
        root.full_clean()
    root.parent = None

    root = update_assigned_task(
        actor=employee,
        task=root,
        status=Task.Status.IN_PROGRESS,
        actual_hours=Decimal("2.50"),
        blocking_reason="",
    )
    with pytest.raises(ValidationError):
        update_assigned_task(
            actor=employee,
            task=root,
            status=Task.Status.BLOCKED,
            actual_hours=Decimal("3.00"),
            blocking_reason="",
        )
    comment = add_task_comment(actor=employee, task=root, body="تم إنجاز الجزء الأول.")
    comment.body = "Changed"
    with pytest.raises(PermissionDenied):
        comment.save()

    tag = save_tag(
        actor=manager,
        code="URGENT",
        name_ar="عاجل",
        name_en="Urgent",
    )
    replace_task_tags(actor=manager, task=root, tags=[tag])
    assert root.tag_links.filter(tag=tag, removed_at__isnull=True).exists()
    assert TaskAssignment.objects.get(task=root, removed_at__isnull=True).is_primary

    with pytest.raises(ValidationError):
        archive_task(actor=manager, task=root)
    with pytest.raises(ValidationError):
        archive_project(actor=manager, project=project)
    archive_task(actor=manager, task=grandchild)
    archive_task(actor=manager, task=child)
    archive_task(actor=manager, task=root)
    root = restore_task(actor=manager, task=root)
    assert root.assignments.filter(
        user=employee,
        is_primary=True,
        removed_at__isnull=True,
    ).exists()
    archive_task(actor=manager, task=root)
    project = archive_project(actor=manager, project=project)
    assert project.is_archived
    assert AuditEvent.objects.filter(
        scope=AuditEvent.Scope.TASKS,
        action=actions.TASK_CREATED,
        target_id=str(root.pk),
    ).exists()
    assert AuditEvent.objects.filter(
        scope=AuditEvent.Scope.TASKS,
        action=actions.TASK_COMMENT_ADDED,
        target_id=str(root.pk),
    ).exists()
    with pytest.raises(PermissionDenied):
        Task.objects.filter(pk=root.pk).delete()


@pytest.mark.integration
@pytest.mark.django_db
def test_task_owner_dates_status_and_assignment_validation() -> None:
    department = Department.objects.create(
        code="QA5", name_ar="الجودة", name_en="Quality"
    )
    manager = role_user("phase5-qa-manager", "project_manager", department)
    employee = role_user("phase5-qa-employee", "employee", department)
    outsider = role_user("phase5-qa-outsider", "employee", department)
    project = make_project(code="PRJ-T03", department=department, manager=manager)
    ProjectMembership.objects.create(project=project, user=employee, added_by=manager)
    course = Course.objects.create(
        code="CRS-T03",
        project=project,
        name_ar="دورة الجودة",
        name_en="Quality Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=20,
        start_at=datetime(2026, 9, 1, 6, tzinfo=UTC),
        end_at=datetime(2026, 9, 3, 12, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )

    with pytest.raises(ValidationError):
        create_task(
            actor=manager,
            assignees=[employee],
            primary_owner=employee,
            code="TSK-BAD-DATE",
            project=None,
            course=course,
            parent=None,
            name_ar="مهمة خارج الجدول",
            name_en="Out-of-schedule task",
            description="",
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            start_date=date(2026, 8, 31),
            due_date=date(2026, 9, 2),
            estimated_hours=None,
            actual_hours=None,
            blocking_reason="",
        )
    course_task = create_task(
        actor=manager,
        assignees=[employee],
        primary_owner=employee,
        code="TSK-COURSE",
        project=None,
        course=course,
        parent=None,
        name_ar="مهمة الدورة",
        name_en="Course task",
        description="",
        status=Task.Status.TODO,
        priority=Task.Priority.MEDIUM,
        start_date=date(2026, 9, 1),
        due_date=date(2026, 9, 2),
        estimated_hours=None,
        actual_hours=None,
        blocking_reason="",
    )
    assert course_task.course == course
    with pytest.raises(ValidationError):
        archive_course(actor=manager, course=course)
    with pytest.raises(ValidationError):
        create_project_task(
            actor=manager,
            project=project,
            assignee=employee,
            code="TSK-BLOCKED",
            status=Task.Status.BLOCKED,
        )
    with pytest.raises(ValidationError):
        create_task(
            actor=manager,
            assignees=[employee],
            primary_owner=outsider,
            code="TSK-BAD-OWNER",
            project=project,
            course=None,
            parent=None,
            name_ar="مالك غير صالح",
            name_en="Invalid primary",
            description="",
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            start_date=None,
            due_date=None,
            estimated_hours=None,
            actual_hours=None,
            blocking_reason="",
        )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_private_task_file_validation_and_authorized_download(tmp_path: Path) -> None:
    department = Department.objects.create(
        code="DOC5", name_ar="الوثائق", name_en="Documents"
    )
    manager = role_user("phase5-file-manager", "project_manager", department)
    employee = role_user("phase5-file-employee", "employee", department)
    outsider = role_user("phase5-file-outsider", "employee", department)
    project = make_project(code="PRJ-T04", department=department, manager=manager)
    ProjectMembership.objects.create(project=project, user=employee, added_by=manager)
    task = create_project_task(
        actor=manager,
        project=project,
        assignee=employee,
        code="TSK-FILE",
    )
    valid_upload = SimpleUploadedFile(
        "evidence.pdf",
        b"%PDF-1.4\n1 0 obj\n%%EOF",
        content_type="application/pdf",
    )
    invalid_upload = SimpleUploadedFile(
        "fake.pdf",
        b"not a pdf",
        content_type="application/pdf",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        record = upload_task_file(actor=employee, task=task, upload=valid_upload)
        with pytest.raises(ValidationError):
            upload_task_file(actor=employee, task=task, upload=invalid_upload)
        assert TaskFile.objects.get(pk=record.pk).sha256

        client = WebClient()
        client.force_login(employee)
        response = client.get(reverse("tasks:file_download", args=(record.pk,)))
        assert response.status_code == 200
        assert response["X-Content-Type-Options"] == "nosniff"
        client.force_login(outsider)
        assert (
            client.get(reverse("tasks:file_download", args=(record.pk,))).status_code
            == 404
        )
