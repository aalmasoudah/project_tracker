"""Phase 4 course, trainer, file, permission, and lifecycle tests."""

from datetime import UTC, date, datetime
from importlib import import_module
from pathlib import Path
from typing import TypedDict, cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as WebClient
from django.urls import reverse

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.courses.forms import CourseForm, TrainerForm
from apps.courses.models import Course, CourseFile, CourseTrainerAssignment, Trainer
from apps.courses.selectors import courses_visible_to
from apps.courses.services import (
    archive_course,
    create_course,
    replace_course_trainers,
    save_trainer,
    set_trainer_archived,
    update_course,
    upload_course_file,
)
from apps.organizations.models import Department
from apps.projects.models import Project, ProjectMembership
from apps.projects.services import archive_project, update_project

PHASE4_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.courses.migrations.0002_seed_phase4_permissions"
    ).ROLE_COURSE_PERMISSIONS,
)


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase4-password-7162",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def make_project(
    *,
    code: str,
    department: Department,
    manager: User,
    status: str = Project.Status.ACTIVE,
) -> Project:
    return Project.objects.create(
        code=code,
        name_ar="مشروع التدريب",
        name_en="Training Project",
        department=department,
        manager=manager,
        status=status,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=manager,
        updated_by=manager,
    )


class CourseData(TypedDict):
    code: str
    project: Project
    name_ar: str
    name_en: str
    description: str
    delivery_type: str
    location: str
    capacity: int
    start_at: datetime
    end_at: datetime
    status: str
    notes: str


def course_data(project: Project, *, code: str = "CRS-101") -> CourseData:
    return {
        "code": code,
        "project": project,
        "name_ar": "دورة إدارة المشاريع",
        "name_en": "Project Management Course",
        "description": "تدريب عملي",
        "delivery_type": Course.DeliveryType.IN_PERSON,
        "location": "الرياض",
        "capacity": 25,
        "start_at": datetime(2026, 9, 1, 6, tzinfo=UTC),
        "end_at": datetime(2026, 9, 3, 12, tzinfo=UTC),
        "status": Course.Status.DRAFT,
        "notes": "",
    }


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_approved_phase4_matrix() -> None:
    for role_code, permission_keys in PHASE4_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="courses"
            )
        }
        assert actual == permission_keys


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_course_visibility_contact_privacy_and_direct_url_denial() -> None:
    department = Department.objects.create(
        code="LND", name_ar="التعلم", name_en="Learning"
    )
    other_department = Department.objects.create(
        code="OTH", name_ar="أخرى", name_en="Other"
    )
    manager = role_user("course-manager", "project_manager", department)
    supervisor = role_user("course-supervisor", "supervisor", department)
    employee = role_user("course-employee", "employee", department)
    outsider = role_user("course-outsider", "employee", other_department)
    project = make_project(code="PRJ-C01", department=department, manager=manager)
    project.supervisor = supervisor
    project.save(update_fields=("supervisor",))
    ProjectMembership.objects.create(project=project, user=employee, added_by=manager)
    course = create_course(actor=manager, **course_data(project))
    changed = course_data(project)
    changed["status"] = Course.Status.ACTIVE
    course = update_course(actor=manager, course=course, **changed)
    trainer = Trainer.objects.create(
        code="TR-01",
        name_ar="أحمد المدرب",
        name_en="Ahmed Trainer",
        email="ahmed@example.test",
        created_by=manager,
        updated_by=manager,
    )
    replace_course_trainers(actor=manager, course=course, trainers=[trainer])

    assert set(courses_visible_to(manager)) == {course}
    assert set(courses_visible_to(supervisor)) == {course}
    assert set(courses_visible_to(employee)) == {course}
    assert not courses_visible_to(outsider).exists()

    client = WebClient()
    client.force_login(employee)
    response = client.get(reverse("courses:detail", args=(course.pk,)))
    assert response.status_code == 200
    assert "أحمد المدرب" in response.content.decode()
    assert "ahmed@example.test" not in response.content.decode()

    client.force_login(manager)
    assert (
        "ahmed@example.test"
        in client.get(reverse("courses:detail", args=(course.pk,))).content.decode()
    )

    client.force_login(outsider)
    assert client.get(reverse("courses:detail", args=(course.pk,))).status_code == 404


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_course_trainer_archive_history_and_project_guards() -> None:
    department = Department.objects.create(
        code="OPS4", name_ar="العمليات", name_en="Operations"
    )
    manager = role_user("phase4-manager", "project_manager", department)
    executive = role_user("phase4-executive", "executive_manager", department)
    project = make_project(code="PRJ-C02", department=department, manager=manager)
    course = create_course(actor=manager, **course_data(project, code="CRS-202"))
    changed = course_data(project, code=course.code)
    changed["status"] = Course.Status.ACTIVE
    course = update_course(actor=manager, course=course, **changed)
    trainer = save_trainer(
        actor=executive,
        code="TR-02",
        name_ar="سارة المدربة",
        name_en="Sarah Trainer",
        email="sarah@example.test",
        phone="+966500000000",
        organization="Training Co",
        notes="",
    )
    replace_course_trainers(actor=manager, course=course, trainers=[trainer])

    with pytest.raises(ValidationError):
        set_trainer_archived(actor=executive, trainer=trainer, archived=True)
    with pytest.raises(ValidationError):
        archive_project(actor=manager, project=project)

    project_data = {
        field: getattr(project, field)
        for field in (
            "code",
            "name_ar",
            "name_en",
            "department",
            "client",
            "category",
            "manager",
            "supervisor",
            "status",
            "priority",
            "start_date",
            "end_date",
            "budget",
            "goals",
            "requirements",
            "notes",
        )
    }
    project_data["status"] = Project.Status.ON_HOLD
    with pytest.raises(ValidationError):
        update_project(actor=manager, project=project, **project_data)

    course = archive_course(actor=manager, course=course)
    assert course.is_archived
    assert CourseTrainerAssignment.objects.filter(
        course=course, trainer=trainer, removed_at__isnull=False
    ).exists()
    set_trainer_archived(actor=executive, trainer=trainer, archived=True)
    assert AuditEvent.objects.filter(
        scope=AuditEvent.Scope.COURSES,
        action=actions.COURSE_ARCHIVED,
        target_id=str(course.pk),
    ).exists()
    with pytest.raises(PermissionDenied):
        Course.objects.filter(pk=course.pk).delete()


@pytest.mark.integration
@pytest.mark.django_db
def test_forms_reject_invalid_schedule_capacity_location_and_duplicates() -> None:
    department = Department.objects.create(
        code="QA4", name_ar="الجودة", name_en="Quality"
    )
    manager = role_user("phase4-qa-manager", "project_manager", department)
    project = make_project(code="PRJ-C03", department=department, manager=manager)
    data = {
        "code": "CRS-303",
        "project": str(project.pk),
        "name_ar": "دورة الجودة",
        "name_en": "Quality Course",
        "delivery_type": Course.DeliveryType.IN_PERSON,
        "location": "",
        "capacity": "0",
        "start_at": "2026-09-03T12:00",
        "end_at": "2026-09-03T11:00",
        "status": Course.Status.DRAFT,
        "description": "",
        "notes": "",
    }
    form = CourseForm(data=data, actor=manager)
    assert not form.is_valid()
    assert {"location", "capacity", "end_at"} <= set(form.errors)

    Trainer.objects.create(
        code="TR-03",
        name_ar="مدرب",
        name_en="Trainer",
        email="duplicate@example.test",
        created_by=manager,
        updated_by=manager,
    )
    trainer_form = TrainerForm(
        data={
            "code": "TR-04",
            "name_ar": "مدرب آخر",
            "name_en": "Other Trainer",
            "email": "DUPLICATE@example.test",
            "phone": "",
            "organization": "",
            "notes": "",
        }
    )
    assert not trainer_form.is_valid()
    assert "email" in trainer_form.errors


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_private_course_file_validation_and_authorized_download(tmp_path: Path) -> None:
    department = Department.objects.create(
        code="DOC4", name_ar="الوثائق", name_en="Documents"
    )
    other_department = Department.objects.create(
        code="OUT4", name_ar="الخارج", name_en="Outside"
    )
    manager = role_user("file-manager", "project_manager", department)
    outsider = role_user("file-outsider", "employee", other_department)
    project = make_project(code="PRJ-C04", department=department, manager=manager)
    course = create_course(actor=manager, **course_data(project, code="CRS-404"))

    valid = SimpleUploadedFile(
        "guide.pdf",
        b"%PDF-1.7\nfictional training guide\n%%EOF",
        content_type="application/pdf",
    )
    from django.test import override_settings

    with override_settings(MEDIA_ROOT=tmp_path):
        record = upload_course_file(actor=manager, course=course, upload=valid)
        assert CourseFile.objects.filter(pk=record.pk).exists()
        assert record.file.name != record.original_name

        client = WebClient()
        client.force_login(manager)
        response = client.get(reverse("courses:file_download", args=(record.pk,)))
        assert response.status_code == 200
        assert response["Content-Type"] == "application/octet-stream"
        assert "attachment" in response["Content-Disposition"]

        client.force_login(outsider)
        assert (
            client.get(reverse("courses:file_download", args=(record.pk,))).status_code
            == 404
        )

    invalid = SimpleUploadedFile(
        "fake.pdf", b"not a pdf", content_type="application/pdf"
    )
    with pytest.raises(ValidationError):
        upload_course_file(actor=manager, course=course, upload=invalid)
