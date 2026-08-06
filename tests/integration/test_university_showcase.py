"""Development-only fictional showcase loader integration tests."""

from io import StringIO

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.accounts.roles import ROLE_CODES
from apps.approvals.models import ApprovalRequest
from apps.attendance.models import AttendanceCorrection, AttendanceSubmission
from apps.courses.models import Course
from apps.projects.models import Client, Project
from apps.tasks.models import Task
from apps.trainees.models import ImportBatch, Trainee


@pytest.mark.integration
@pytest.mark.django_db
@override_settings(DEPLOYMENT_ENVIRONMENT="development")
def test_showcase_loader_retains_zx_and_covers_major_features() -> None:
    for role_code in ROLE_CODES:
        group, _created = Group.objects.get_or_create(name=role_code)
        group.permissions.set(Permission.objects.all())
    zx = User.objects.create_superuser(
        username="zx",
        email="zx@example.test",
        display_name="Technical Admin ZX",
        password="existing-zx-password-2026",
    )
    zx.groups.add(Group.objects.get(name="technical_admin"))
    User.objects.create_user(
        username="remove-me",
        email="remove@example.test",
        display_name="Remove Me",
        password="remove-me-password-2026",
    )
    output = StringIO()

    call_command(
        "load_university_showcase",
        environment="development",
        demo_password="Fictional-Showcase-2026!",
        apply=True,
        confirm="LOAD-UNIVERSITY-SHOWCASE:development",
        stdout=output,
    )

    retained = User.objects.get(username="zx")
    assert retained.check_password("existing-zx-password-2026")
    assert retained.is_superuser
    assert retained.groups.filter(name="technical_admin").exists()
    assert not User.objects.filter(username="remove-me").exists()
    assert User.objects.filter(username="demo.executive", groups__name="ceo").exists()
    assert set(Client.objects.values_list("code", flat=True)) == {"KAU", "KSU", "KKU"}
    assert Project.objects.count() == 7
    assert Course.objects.count() == 3
    assert Task.objects.filter(
        status=Task.Status.BLOCKED, due_date__isnull=False
    ).exists()
    assert Task.objects.filter(is_archived=True).exists()
    assert ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.APPROVED
    ).exists()
    assert ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.REJECTED
    ).exists()
    assert ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.PENDING_MANAGER
    ).exists()
    assert Trainee.objects.count() == 12
    assert ImportBatch.objects.filter(status=ImportBatch.Status.CONFIRMED).exists()
    assert ImportBatch.objects.filter(status=ImportBatch.Status.CANCELLED).exists()
    assert AttendanceSubmission.objects.filter(
        state=AttendanceSubmission.State.APPROVED
    ).exists()
    assert AttendanceSubmission.objects.filter(
        state=AttendanceSubmission.State.PENDING_REVIEW
    ).exists()
    assert AttendanceCorrection.objects.exists()
    assert "showcase-loaded" in output.getvalue()


@pytest.mark.integration
@pytest.mark.django_db
def test_showcase_loader_refuses_non_development_environment() -> None:
    with pytest.raises(CommandError, match="only in development"):
        call_command(
            "load_university_showcase",
            environment="test",
            demo_password="Fictional-Showcase-2026!",
            apply=True,
            confirm="LOAD-UNIVERSITY-SHOWCASE:test",
        )
