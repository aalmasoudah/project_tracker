"""Phase 7 milestone, approval, authorization, and transaction tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import import_module
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.approvals.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStep,
    Milestone,
)
from apps.approvals.selectors import approval_requests_visible_to
from apps.approvals.services import (
    approve_request,
    archive_milestone,
    create_milestone,
    reject_request,
    submit_completion,
    update_milestone,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.courses.models import Course
from apps.organizations.models import Department
from apps.progress.services import calculate_project_progress
from apps.projects.models import Project, ProjectMembership
from apps.tasks.models import Task, TaskAssignment
from apps.tasks.services import update_assigned_task

PHASE7_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.approvals.migrations.0002_seed_phase7_permissions"
    ).ROLE_APPROVAL_PERMISSIONS,
)


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase7-password-4816",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def make_project(
    *,
    code: str,
    department: Department,
    manager: User,
    supervisor: User,
) -> Project:
    return Project.objects.create(
        code=code,
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


def make_task(
    *,
    code: str,
    project: Project,
    actor: User,
    assignee: User,
    status: str = Task.Status.COMPLETED,
) -> Task:
    task = Task.objects.create(
        code=code,
        project=project,
        name_ar=f"مهمة {code}",
        name_en=f"Task {code}",
        status=status,
        priority=Task.Priority.HIGH,
        created_by=actor,
        updated_by=actor,
    )
    TaskAssignment.objects.create(
        task=task,
        user=assignee,
        is_primary=True,
        assigned_by=actor,
    )
    return task


@pytest.mark.integration
@pytest.mark.django_db
def test_approval_queue_and_milestone_list_render_shared_pagination() -> None:
    department = Department.objects.create(
        code="PGN7",
        name_ar="إدارة الموافقات",
        name_en="Approvals",
    )
    manager = role_user("pagination-manager", "project_manager", department)
    client = Client()
    client.force_login(manager)

    approval_response = client.get(
        reverse("approvals:queue"),
        {"status": ApprovalRequest.Status.PENDING_SUPERVISOR},
    )
    milestone_response = client.get(reverse("approvals:milestone_list"))

    assert approval_response.status_code == 200
    assert milestone_response.status_code == 200
    assert "includes/pagination.html" in {
        template.name for template in approval_response.templates
    }
    assert "includes/pagination.html" in {
        template.name for template in milestone_response.templates
    }


def decide_both(
    approval_request: ApprovalRequest,
    *,
    supervisor: User,
    manager: User,
) -> ApprovalRequest:
    approve_request(actor=supervisor, approval_request=approval_request)
    return approve_request(actor=manager, approval_request=approval_request)


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_approved_phase7_matrix() -> None:
    for role_code, permission_keys in PHASE7_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="approvals"
            )
        }
        assert actual == permission_keys


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_milestone_lifecycle_two_step_completion_and_immutable_history() -> None:
    department = Department.objects.create(
        code="APP7", name_ar="إدارة الموافقات", name_en="Approvals"
    )
    manager = role_user("approval-manager", "project_manager", department)
    supervisor = role_user("approval-supervisor", "supervisor", department)
    project = make_project(
        code="PRJ-A71",
        department=department,
        manager=manager,
        supervisor=supervisor,
    )
    milestone = create_milestone(
        actor=manager,
        code="MLS-A71",
        project=project,
        name_ar="جاهزية الإطلاق",
        name_en="Launch Readiness",
        description="Fictional milestone.",
        start_date=date(2026, 8, 10),
        due_date=date(2026, 9, 1),
        status=Milestone.Status.DRAFT,
    )
    milestone = update_milestone(
        actor=manager,
        milestone=milestone,
        code=milestone.code,
        project=project,
        name_ar=milestone.name_ar,
        name_en=milestone.name_en,
        description=milestone.description,
        start_date=milestone.start_date,
        due_date=milestone.due_date,
        status=Milestone.Status.IN_PROGRESS,
    )
    approval_request = submit_completion(actor=manager, target=milestone)
    milestone.refresh_from_db()

    assert milestone.status == Milestone.Status.PENDING_APPROVAL
    assert approval_request.status == ApprovalRequest.Status.PENDING_SUPERVISOR
    assert list(
        approval_request.steps.values_list("role", "status", "approver_id")
    ) == [
        (
            ApprovalStep.Role.SUPERVISOR,
            ApprovalStep.Status.PENDING,
            supervisor.pk,
        ),
        (
            ApprovalStep.Role.PROJECT_MANAGER,
            ApprovalStep.Status.WAITING,
            manager.pk,
        ),
    ]
    with pytest.raises(PermissionDenied):
        update_milestone(
            actor=manager,
            milestone=milestone,
            code=milestone.code,
            project=project,
            name_ar=milestone.name_ar,
            name_en=milestone.name_en,
            description=milestone.description,
            start_date=milestone.start_date,
            due_date=milestone.due_date,
            status=milestone.status,
        )
    with pytest.raises(ValidationError):
        archive_milestone(actor=manager, milestone=milestone)

    decide_both(
        approval_request,
        supervisor=supervisor,
        manager=manager,
    )
    milestone.refresh_from_db()
    approval_request.refresh_from_db()

    assert milestone.status == Milestone.Status.COMPLETED
    assert approval_request.status == ApprovalRequest.Status.APPROVED
    assert approval_request.resolved_at is not None
    assert (
        ApprovalDecision.objects.filter(
            step__request=approval_request,
            outcome=ApprovalDecision.Outcome.APPROVED,
        ).count()
        == 2
    )
    assert calculate_project_progress(project).percentage == Decimal("100.00")
    decision = ApprovalDecision.objects.filter(step__request=approval_request).first()
    assert decision is not None
    with pytest.raises(PermissionDenied):
        ApprovalDecision.objects.filter(pk=decision.pk).update(reason="changed")
    with pytest.raises(PermissionDenied):
        decision.delete()
    assert (
        AuditEvent.objects.filter(
            scope=AuditEvent.Scope.APPROVALS,
            action__in=(
                actions.MILESTONE_CREATED,
                actions.MILESTONE_UPDATED,
                actions.APPROVAL_SUBMITTED,
                actions.APPROVAL_APPROVED,
            ),
        ).count()
        == 5
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_task_rejection_resubmission_wrong_actor_and_private_history() -> None:
    department = Department.objects.create(
        code="REJ7", name_ar="إدارة المراجعة", name_en="Review"
    )
    manager = role_user("reject-manager", "project_manager", department)
    supervisor = role_user("reject-supervisor", "supervisor", department)
    wrong_supervisor = role_user("wrong-supervisor", "supervisor", department)
    employee = role_user("approval-employee", "employee", department)
    other_employee = role_user("other-employee", "employee", department)
    ceo = role_user("approval-ceo", "ceo", department)
    project = make_project(
        code="PRJ-A72",
        department=department,
        manager=manager,
        supervisor=supervisor,
    )
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    task = make_task(
        code="TSK-A71",
        project=project,
        actor=manager,
        assignee=employee,
    )
    first_request = submit_completion(actor=employee, target=task)

    with pytest.raises(ValidationError):
        reject_request(
            actor=supervisor,
            approval_request=first_request,
            reason=" ",
        )
    with pytest.raises(PermissionDenied):
        approve_request(
            actor=wrong_supervisor,
            approval_request=first_request,
        )
    reject_request(
        actor=supervisor,
        approval_request=first_request,
        reason="The completion evidence is incomplete.",
    )
    task.refresh_from_db()
    assert task.status == Task.Status.IN_PROGRESS

    update_assigned_task(
        actor=employee,
        task=task,
        status=Task.Status.COMPLETED,
        actual_hours=None,
        blocking_reason="",
    )
    second_request = submit_completion(actor=employee, target=task)
    assert second_request.attempt == 2
    approve_request(actor=supervisor, approval_request=second_request)
    with pytest.raises(PermissionDenied):
        approve_request(actor=supervisor, approval_request=second_request)
    approve_request(actor=manager, approval_request=second_request)
    task.refresh_from_db()

    assert task.status == Task.Status.COMPLETED
    assert first_request.steps.get(sequence=1).decision.reason == (
        "The completion evidence is incomplete."
    )
    assert set(approval_requests_visible_to(employee)) == {
        first_request,
        second_request,
    }
    assert not approval_requests_visible_to(other_employee).exists()
    assert set(approval_requests_visible_to(ceo)) == {
        first_request,
        second_request,
    }

    client = Client()
    client.force_login(other_employee)
    assert (
        client.get(reverse("approvals:detail", args=(first_request.pk,))).status_code
        == 404
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_course_then_project_completion_requires_centralized_progress() -> None:
    department = Department.objects.create(
        code="CMP7", name_ar="إدارة الإنجاز", name_en="Completion"
    )
    manager = role_user("completion-manager", "project_manager", department)
    supervisor = role_user("completion-supervisor", "supervisor", department)
    project = make_project(
        code="PRJ-A73",
        department=department,
        manager=manager,
        supervisor=supervisor,
    )
    course = Course.objects.create(
        code="CRS-A71",
        project=project,
        name_ar="دورة مكتملة",
        name_en="Completed Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=20,
        start_at=datetime(2026, 9, 1, 8, tzinfo=UTC),
        end_at=datetime(2026, 9, 1, 16, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )
    employee = role_user("course-owner", "employee", department)
    make_task(
        code="TSK-A72",
        project=project,
        actor=manager,
        assignee=employee,
        status=Task.Status.TODO,
    )
    course_task = Task.objects.create(
        code="TSK-A73",
        course=course,
        name_ar="مهمة الدورة",
        name_en="Course Task",
        status=Task.Status.COMPLETED,
        priority=Task.Priority.HIGH,
        created_by=manager,
        updated_by=manager,
    )
    TaskAssignment.objects.create(
        task=course_task,
        user=manager,
        is_primary=True,
        assigned_by=manager,
    )

    course_request = submit_completion(actor=manager, target=course)
    decide_both(course_request, supervisor=supervisor, manager=manager)
    course.refresh_from_db()
    assert course.status == Course.Status.COMPLETED

    with pytest.raises(ValidationError, match="100"):
        submit_completion(actor=manager, target=project)

    project_task = Task.objects.get(code="TSK-A72")
    project_task.status = Task.Status.COMPLETED
    project_task.save(update_fields=("status", "updated_at"))
    project_request = submit_completion(actor=manager, target=project)
    decide_both(project_request, supervisor=supervisor, manager=manager)
    project.refresh_from_db()
    assert project.status == Project.Status.COMPLETED
    assert project_request not in approval_requests_visible_to(supervisor)
    assert project_request in approval_requests_visible_to(manager)
