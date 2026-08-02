"""Phase 14 audit, archive, operations, command, and security integration."""

from datetime import date, timedelta
from importlib import import_module
from io import StringIO
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.operations.services import record_backup_verification
from apps.organizations.models import Department
from apps.projects.models import Project

AUDIT_ROLE_PERMISSIONS = cast(
    "dict[str, set[str]]",
    import_module(
        "apps.audit.migrations.0010_seed_phase14_audit_permissions"
    ).ROLE_PERMISSIONS,
)
OPERATIONS_ROLE_PERMISSIONS = cast(
    "dict[str, set[str]]",
    import_module(
        "apps.operations.migrations.0002_seed_phase14_permissions"
    ).ROLE_PERMISSIONS,
)
PASSWORD = "fictional-phase14-password-8842"


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password=PASSWORD,
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def archived_project(
    code: str,
    manager: User,
    department: Department,
) -> Project:
    return Project.objects.create(
        code=code,
        name_ar=f"مشروع {code}",
        name_en=f"Project {code}",
        department=department,
        manager=manager,
        status=Project.Status.DRAFT,
        priority=Project.Priority.MEDIUM,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_archived=True,
        archived_at=timezone.now(),
        archived_by=manager,
        created_by=manager,
        updated_by=manager,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_phase14_permissions_match_the_approved_matrix() -> None:
    for role, expected in AUDIT_ROLE_PERMISSIONS.items():
        actual = set(
            Group.objects.get(name=role)
            .permissions.filter(
                content_type__app_label="audit",
                codename__in={
                    "view_security_audit",
                    "view_business_audit",
                    "export_security_audit",
                    "export_business_audit",
                },
            )
            .values_list("codename", flat=True)
        )
        assert actual == expected
    for role, expected in OPERATIONS_ROLE_PERMISSIONS.items():
        actual = set(
            Group.objects.get(name=role)
            .permissions.filter(content_type__app_label="operations")
            .values_list("codename", flat=True)
        )
        assert actual == expected


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_central_audit_scopes_details_and_denials_are_isolated() -> None:
    department = Department.objects.create(
        code="AUD14",
        name_ar="إدارة التدقيق",
        name_en="Audit",
    )
    technical = role_user("audit-technical", "technical_admin", department)
    chief = role_user("audit-chief", "ceo", department)
    employee = role_user("audit-employee", "employee", department)
    security_event = AuditEvent.objects.create(
        scope=AuditEvent.Scope.SECURITY,
        actor=technical,
        action=actions.ACCOUNT_UPDATED,
        target_type="account",
        target_id=str(employee.pk),
        target_label=employee.display_name,
        metadata={
            "status": "active",
            "name": "private-filename.pdf",
            "password": "must-not-render",
        },
        correlation_id="security-14",
        ip_address="192.0.2.14",
    )
    business_event = record_audit_event(
        actor=chief,
        scope=AuditEvent.Scope.PROJECTS,
        action=actions.PROJECT_UPDATED,
        target_type="project",
        target_id="14",
        target_label="PRJ-14",
    )
    client = Client()

    client.force_login(technical)
    response = client.get(reverse("audit:list"))
    assert response.status_code == 200
    assert security_event in response.context["page"].object_list
    assert business_event not in response.context["page"].object_list
    detail = client.get(reverse("audit:detail", args=(security_event.pk,)))
    content = detail.content.decode()
    assert detail.status_code == 200
    assert "192.0.2.14" in content
    assert "private-filename.pdf" not in content
    assert "must-not-render" not in content
    assert (
        client.get(reverse("audit:detail", args=(business_event.pk,))).status_code
        == 404
    )

    client.force_login(chief)
    response = client.get(reverse("audit:list"))
    assert business_event in response.context["page"].object_list
    assert security_event not in response.context["page"].object_list
    assert (
        client.get(reverse("audit:detail", args=(security_event.pk,))).status_code
        == 404
    )

    client.force_login(employee)
    assert client.get(reverse("audit:list")).status_code == 403


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_audit_filters_and_csv_export_are_bounded_and_formula_safe() -> None:
    department = Department.objects.create(
        code="EXP14",
        name_ar="إدارة التصدير",
        name_en="Export",
    )
    chief = role_user("export-chief", "ceo", department)
    event = record_audit_event(
        actor=chief,
        scope=AuditEvent.Scope.PROJECTS,
        action=actions.PROJECT_UPDATED,
        target_type="project",
        target_id="=2+2",
        target_label="=SUM(A1:A2)",
        metadata={"name": "private.pdf", "status": "active"},
    )
    client = Client()
    client.force_login(chief)
    today = timezone.localdate()
    valid = {
        "scope": AuditEvent.Scope.PROJECTS,
        "action": actions.PROJECT_UPDATED,
        "target_type": "project",
        "date_from": today.isoformat(),
        "date_to": today.isoformat(),
    }

    response = client.post(reverse("audit:export"), valid)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert response["Cache-Control"] == "no-store, private"
    content = response.content.decode("utf-8-sig")
    assert "'=SUM(A1:A2)" in content
    assert "private.pdf" not in content
    assert event.correlation_id in content
    assert AuditEvent.objects.filter(
        action=actions.AUDIT_EXPORTED,
        scope=AuditEvent.Scope.OPERATIONS,
    ).exists()

    forged = dict(valid, scope=AuditEvent.Scope.SECURITY)
    assert client.post(reverse("audit:export"), forged).status_code == 400
    excessive = dict(valid, date_from="2024-01-01")
    assert client.get(reverse("audit:list"), excessive).status_code == 400


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_archive_center_reuses_existing_role_and_object_scope() -> None:
    department = Department.objects.create(
        code="ARC14",
        name_ar="إدارة الأرشيف",
        name_en="Archive",
    )
    first_manager = role_user("archive-first", "project_manager", department)
    second_manager = role_user("archive-second", "project_manager", department)
    executive = role_user("archive-executive", "executive_manager", department)
    technical = role_user("archive-technical", "technical_admin", department)
    employee = role_user("archive-employee", "employee", department)
    first = archived_project("ARC-ONE", first_manager, department)
    second = archived_project("ARC-TWO", second_manager, department)
    archived_department = Department.objects.create(
        code="OLD14",
        name_ar="إدارة قديمة",
        name_en="Old department",
        is_archived=True,
        archived_at=timezone.now(),
    )
    client = Client()

    client.force_login(first_manager)
    response = client.get(
        reverse("operations:archives"),
        {"record_type": "project"},
    )
    assert response.status_code == 200
    assert first.code in response.content.decode()
    assert second.code not in response.content.decode()

    client.force_login(executive)
    response = client.get(
        reverse("operations:archives"),
        {"record_type": "project"},
    )
    assert first.code in response.content.decode()
    assert second.code in response.content.decode()

    client.force_login(technical)
    response = client.get(
        reverse("operations:archives"),
        {"record_type": "department"},
    )
    assert archived_department.code in response.content.decode()
    assert (
        client.get(
            reverse("operations:archives"),
            {"record_type": "project"},
        ).status_code
        == 400
    )

    client.force_login(employee)
    assert client.get(reverse("operations:archives")).status_code == 403


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_safe_operations_status_has_no_restore_action_or_secret() -> None:
    department = Department.objects.create(
        code="OPS14",
        name_ar="إدارة العمليات",
        name_en="Operations",
    )
    technical = role_user("ops-technical", "technical_admin", department)
    chief = role_user("ops-chief", "ceo", department)
    record_backup_verification(
        kind="backup",
        environment="test",
        status="succeeded",
        completed_at=timezone.now(),
    )
    client = Client()
    client.force_login(technical)
    response = client.get(reverse("operations:status"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "DATABASE_URL" not in content
    assert "password" not in content.lower()
    assert "/restore/" not in content
    assert reverse("operations:status") != "/health/"

    client.force_login(chief)
    assert client.get(reverse("operations:status")).status_code == 403


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
@override_settings(DEPLOYMENT_ENVIRONMENT="test")
def test_protected_commands_are_dry_run_confirmed_and_idempotent() -> None:
    completed_at = timezone.now().isoformat()
    output = StringIO()
    call_command(
        "record_backup_status",
        environment="test",
        kind="backup",
        status="succeeded",
        completed_at=completed_at,
        stdout=output,
    )
    assert "DRY-RUN" in output.getvalue()
    assert not AuditEvent.objects.filter(action=actions.BACKUP_STATUS_RECORDED).exists()

    with pytest.raises(CommandError):
        call_command(
            "record_backup_status",
            environment="production",
            kind="backup",
            status="succeeded",
            completed_at=completed_at,
        )
    with pytest.raises(CommandError):
        call_command(
            "record_backup_status",
            environment="test",
            kind="backup",
            status="succeeded",
            completed_at=completed_at,
            apply=True,
            confirm="yes",
        )
    with pytest.raises(CommandError):
        call_command(
            "record_backup_status",
            environment="test",
            kind="backup",
            status="succeeded",
            completed_at=(timezone.now() + timedelta(hours=1)).isoformat(),
        )

    options = {
        "environment": "test",
        "kind": "backup",
        "status": "succeeded",
        "completed_at": completed_at,
        "apply": True,
        "confirm": "RECORD-BACKUP-STATUS:test",
    }
    call_command("record_backup_status", **options)
    call_command("record_backup_status", **options)
    assert AuditEvent.objects.filter(action=actions.BACKUP_STATUS_RECORDED).count() == 1

    retention_output = StringIO()
    call_command(
        "retention_inventory",
        environment="test",
        stdout=retention_output,
    )
    assert '"deletion_candidates": 0' in retention_output.getvalue()
    assert "no deletion mode exists" in retention_output.getvalue()
    call_command(
        "retention_inventory",
        environment="test",
        record=True,
        confirm="RECORD-RETENTION-INVENTORY:test",
    )
    assert (
        AuditEvent.objects.filter(action=actions.RETENTION_INVENTORY_RECORDED).count()
        == 1
    )
