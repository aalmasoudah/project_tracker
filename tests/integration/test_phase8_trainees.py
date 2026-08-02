"""Phase 8 lifecycle, import, authorization, and transaction tests."""

from datetime import UTC, date, datetime
from importlib import import_module
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import DjangoAssertNumQueries

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.courses.models import Course
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.trainees.models import CourseEnrollment, ImportBatch, Trainee
from apps.trainees.selectors import enrollments_visible_to
from apps.trainees.services import (
    confirm_import,
    create_enrollment,
    preview_import,
    set_enrollment_archived,
)

PHASE8_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.trainees.migrations.0002_seed_phase8_permissions"
    ).ROLE_PERMISSIONS,
)


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase8-password-4826",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def make_course(
    *, department: Department, manager: User, supervisor: User, code: str = "CRS-8"
) -> Course:
    project = Project.objects.create(
        code=f"PRJ-{code}",
        name_ar="مشروع التدريب",
        name_en="Training Project",
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
    return Course.objects.create(
        code=code,
        project=project,
        name_ar="دورة تجريبية",
        name_en="Fictional Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=3,
        start_at=datetime(2026, 8, 2, 9, tzinfo=UTC),
        end_at=datetime(2026, 8, 3, 15, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_phase8_matrix() -> None:
    for role_code, expected in PHASE8_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="trainees"
            )
        }
        assert actual == expected


@pytest.mark.integration
@pytest.mark.django_db
def test_manual_lifecycle_duplicate_capacity_numbering_and_audit() -> None:
    department = Department.objects.create(
        code="TRN8", name_ar="التدريب", name_en="Training"
    )
    manager = role_user("trainee-manager", "project_manager", department)
    supervisor = role_user("trainee-supervisor", "supervisor", department)
    course = make_course(department=department, manager=manager, supervisor=supervisor)

    first = create_enrollment(
        actor=manager,
        course=course,
        full_name="أحمد علي",
        phone="0500000001",
    )
    assert first.trainee_number == 1
    with pytest.raises(ValidationError):
        create_enrollment(
            actor=manager,
            course=course,
            full_name="احمد  علي",
            phone="+966 50 000 0001",
        )
    set_enrollment_archived(actor=manager, enrollment=first, archived=True)
    second = create_enrollment(
        actor=manager,
        course=course,
        full_name="Fictional Two",
        phone="0500000002",
    )
    assert second.trainee_number == 2
    set_enrollment_archived(actor=manager, enrollment=first, archived=False)
    create_enrollment(
        actor=manager,
        course=course,
        full_name="Fictional Three",
        phone="0500000003",
    )
    with pytest.raises(ValidationError):
        create_enrollment(
            actor=manager,
            course=course,
            full_name="Fictional Four",
            phone="0500000004",
        )
    assert AuditEvent.objects.filter(scope=AuditEvent.Scope.TRAINEES).count() == 5


@pytest.mark.integration
@pytest.mark.django_db
def test_csv_preview_confirm_preserves_order_and_skips_duplicate() -> None:
    department = Department.objects.create(
        code="IMP8", name_ar="الاستيراد", name_en="Imports"
    )
    manager = role_user("import-manager", "project_manager", department)
    supervisor = role_user("import-supervisor", "supervisor", department)
    course = make_course(
        department=department, manager=manager, supervisor=supervisor, code="CRS-IMP8"
    )
    existing = create_enrollment(
        actor=manager,
        course=course,
        full_name="Existing Trainee",
        phone="0500000001",
        email="old@example.test",
    )
    upload = SimpleUploadedFile(
        "trainees.csv",
        (
            "\ufefffull_name,phone,email\n"
            "Existing Trainee,+966500000001,new@example.test\n"
            "متدرب جديد,0500000002,new-ar@example.test\n"
            "New English,0500000003,new-en@example.test\n"
        ).encode(),
        content_type="text/csv",
    )
    batch = preview_import(actor=manager, course=course, upload=upload)
    assert batch.valid_count == 2
    assert batch.duplicate_count == 1
    assert CourseEnrollment.objects.filter(course=course).count() == 1

    duplicate = batch.rows.get(classification="duplicate")
    confirm_import(
        actor=manager,
        batch=batch,
        resolutions={duplicate.pk: "update"},
    )
    assert list(
        CourseEnrollment.objects.filter(course=course).values_list(
            "trainee_number", flat=True
        )
    ) == [1, 2, 3]
    existing.trainee.refresh_from_db()
    assert existing.trainee.email == "new@example.test"
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.CONFIRMED


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_error_and_capacity_confirmation_are_atomic_and_scope_is_private() -> None:
    department = Department.objects.create(
        code="SEC8", name_ar="الخصوصية", name_en="Privacy"
    )
    manager = role_user("private-manager", "project_manager", department)
    other_manager = role_user("other-private-manager", "project_manager", department)
    supervisor = role_user("private-supervisor", "supervisor", department)
    course = make_course(
        department=department, manager=manager, supervisor=supervisor, code="CRS-SEC8"
    )
    invalid = SimpleUploadedFile(
        "invalid.csv",
        b"full_name,phone\nBroken,12\n",
        content_type="text/csv",
    )
    batch = preview_import(actor=manager, course=course, upload=invalid)
    assert batch.error_count == 1
    with pytest.raises(ValidationError):
        confirm_import(actor=manager, batch=batch)
    assert not Trainee.objects.exists()
    with pytest.raises(PermissionDenied):
        preview_import(
            actor=other_manager,
            course=course,
            upload=SimpleUploadedFile(
                "safe.csv",
                b"full_name,phone\nSafe,0500000001\n",
                content_type="text/csv",
            ),
        )
    assert not enrollments_visible_to(other_manager).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_preview_preserves_source_row_numbers_and_rejects_wrong_width() -> None:
    department = Department.objects.create(
        code="ROW8", name_ar="الصفوف", name_en="Rows"
    )
    manager = role_user("row-manager", "project_manager", department)
    supervisor = role_user("row-supervisor", "supervisor", department)
    course = make_course(
        department=department, manager=manager, supervisor=supervisor, code="CRS-ROW8"
    )
    upload = SimpleUploadedFile(
        "rows.csv",
        (
            b"full_name,phone\n"
            b"\n"
            b"Valid Warning,0500000001\n"
            b"Wrong Width,0500000002,unexpected\n"
        ),
        content_type="text/csv",
    )
    batch = preview_import(actor=manager, course=course, upload=upload)
    assert list(batch.rows.values_list("row_number", "classification")) == [
        (3, "warning"),
        (4, "error"),
    ]
    assert batch.warning_count == 1
    assert batch.error_count == 1


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_limited_roster_hides_contact_and_direct_import_history() -> None:
    department = Department.objects.create(
        code="VIEW8", name_ar="العرض", name_en="Visibility"
    )
    manager = role_user("view-manager", "project_manager", department)
    supervisor = role_user("view-supervisor", "supervisor", department)
    course = make_course(
        department=department, manager=manager, supervisor=supervisor, code="CRS-VIEW8"
    )
    enrollment = create_enrollment(
        actor=manager,
        course=course,
        full_name="Private Trainee",
        phone="0500000099",
        email="private@example.test",
    )
    client = Client()
    client.force_login(supervisor)
    response = client.get(reverse("trainees:detail", args=[enrollment.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Private Trainee" in content
    assert "0500000099" not in content
    assert "private@example.test" not in content
    assert client.get(reverse("trainees:import-history")).status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
def test_enrollment_list_uses_one_bounded_query(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    department = Department.objects.create(
        code="QRY8", name_ar="الاستعلام", name_en="Queries"
    )
    manager = role_user("query-manager", "project_manager", department)
    supervisor = role_user("query-supervisor", "supervisor", department)
    course = make_course(
        department=department, manager=manager, supervisor=supervisor, code="CRS-QRY8"
    )
    for number in range(2):
        create_enrollment(
            actor=manager,
            course=course,
            full_name=f"Fictional Query {number}",
            phone=f"050000001{number}",
        )
    with django_assert_num_queries(1):
        records = list(enrollments_visible_to(manager))
        assert [
            (record.trainee.full_name, record.course.project.code) for record in records
        ] == [
            ("Fictional Query 0", "PRJ-CRS-QRY8"),
            ("Fictional Query 1", "PRJ-CRS-QRY8"),
        ]
