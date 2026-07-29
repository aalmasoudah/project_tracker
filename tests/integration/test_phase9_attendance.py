"""Phase 9 scheduling, token isolation, submission, and authorization tests."""

from datetime import UTC, date, datetime, timedelta
from importlib import import_module
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.attendance.models import (
    AttendanceEntry,
    AttendanceSubmission,
    Session,
    TrainerLink,
)
from apps.attendance.services import (
    create_sessions,
    issue_trainer_link,
    submit_attendance,
)
from apps.audit.models import AuditEvent
from apps.courses.models import Course, CourseTrainerAssignment, Trainer
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.trainees.services import create_enrollment

PHASE9_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.attendance.migrations.0002_seed_phase9_permissions"
    ).ROLE_PERMISSIONS,
)


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        password="fictional-phase9-password-4926",
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def setup_course() -> tuple[User, User, Course, Trainer]:
    department = Department.objects.create(
        code="ATT9", name_ar="الحضور", name_en="Attendance"
    )
    manager = role_user("attendance-manager", "project_manager", department)
    supervisor = role_user("attendance-supervisor", "supervisor", department)
    project = Project.objects.create(
        code="PRJ-ATT9",
        name_ar="مشروع الحضور",
        name_en="Attendance Project",
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
    course = Course.objects.create(
        code="CRS-ATT9",
        project=project,
        name_ar="دورة الحضور",
        name_en="Attendance Course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=10,
        start_at=datetime(2026, 8, 2, 9, tzinfo=UTC),
        end_at=datetime(2026, 10, 30, 16, tzinfo=UTC),
        status=Course.Status.ACTIVE,
        created_by=manager,
        updated_by=manager,
    )
    trainer = Trainer.objects.create(
        code="TRN-ATT9",
        name_ar="مدرب خيالي",
        name_en="Fictional Trainer",
        email="trainer-att9@example.test",
        created_by=manager,
        updated_by=manager,
    )
    CourseTrainerAssignment.objects.create(
        course=course, trainer=trainer, assigned_by=manager
    )
    for number in range(2):
        create_enrollment(
            actor=manager,
            course=course,
            full_name=f"متدرب خيالي {number}",
            phone=f"050000002{number}",
        )
    return manager, supervisor, course, trainer


def create_one_session(manager: User, course: Course, trainer: Trainer) -> Session:
    return create_sessions(
        actor=manager,
        course=course,
        trainer=trainer,
        title_ar="جلسة تجريبية",
        title_en="Fictional Session",
        start_at=datetime(2026, 8, 5, 9, tzinfo=UTC),
        end_at=datetime(2026, 8, 5, 11, tzinfo=UTC),
    )[0]


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_roles_exactly_match_phase9_matrix() -> None:
    for role_code, expected in PHASE9_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="attendance"
            )
        }
        assert actual == expected


@pytest.mark.integration
@pytest.mark.django_db
def test_recurrence_is_bounded_idempotent_and_allows_multiple_same_day() -> None:
    manager, _supervisor, course, trainer = setup_course()

    def create_weekly() -> list[Session]:
        return create_sessions(
            actor=manager,
            course=course,
            trainer=trainer,
            title_ar="جلسة أسبوعية",
            title_en="Weekly Session",
            start_at=datetime(2026, 8, 5, 9, tzinfo=UTC),
            end_at=datetime(2026, 8, 5, 11, tzinfo=UTC),
            recurrence=Session.Recurrence.WEEKLY,
            recurrence_count=3,
        )

    sessions = create_weekly()
    assert [item.start_at.date().isoformat() for item in sessions] == [
        "2026-08-05",
        "2026-08-12",
        "2026-08-19",
    ]
    assert [item.pk for item in create_weekly()] == [item.pk for item in sessions]
    create_sessions(
        actor=manager,
        course=course,
        trainer=trainer,
        title_ar="جلسة مسائية",
        title_en="Evening Session",
        start_at=datetime(2026, 8, 5, 13, tzinfo=UTC),
        end_at=datetime(2026, 8, 5, 15, tzinfo=UTC),
    )
    assert Session.objects.count() == 4


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_issue_reissue_hash_only_and_atomic_pending_submission() -> None:
    manager, _supervisor, course, trainer = setup_course()
    session = create_one_session(manager, course, trainer)
    first_link, first_token = issue_trainer_link(
        actor=manager, session=session, lifetime_hours=72
    )
    assert first_token not in first_link.token_hash
    assert not AuditEvent.objects.filter(metadata__icontains=first_token).exists()
    second_link, second_token = issue_trainer_link(
        actor=manager, session=session, lifetime_hours=72
    )
    first_link.refresh_from_db()
    assert first_link.state == TrainerLink.State.REVOKED
    assert first_token != second_token
    participants = list(session.participants.all())
    with pytest.raises(ValidationError):
        submit_attendance(
            link=second_link,
            entries={participants[0].pk: ("present", "")},
            trainer_notes="",
            evidence_files=[],
        )
    assert not AttendanceSubmission.objects.exists()
    entries: dict[int, tuple[str, str]] = {
        participant.pk: (
            AttendanceEntry.Value.PRESENT
            if index == 0
            else AttendanceEntry.Value.EXCUSED,
            "ملاحظة خيالية" if index else "",
        )
        for index, participant in enumerate(participants)
    }
    submission = submit_attendance(
        link=second_link,
        entries=entries,
        trainer_notes="تم التسجيل",
        evidence_files=[],
    )
    assert submission.state == AttendanceSubmission.State.PENDING_REVIEW
    assert submission.entries.count() == 2
    second_link.refresh_from_db()
    assert second_link.state == TrainerLink.State.SUBMITTED
    with pytest.raises(ValidationError):
        submit_attendance(
            link=second_link,
            entries=entries,
            trainer_notes="replay",
            evidence_files=[],
        )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_expiry_rechecked_on_submit_and_external_states_do_not_enumerate() -> None:
    manager, _supervisor, course, trainer = setup_course()
    session = create_one_session(manager, course, trainer)
    link, token = issue_trainer_link(actor=manager, session=session, lifetime_hours=1)
    link.expires_at = timezone.now() - timedelta(seconds=1)
    link.save(update_fields=("expires_at",))
    entries: dict[int, tuple[str, str]] = {
        participant.pk: (AttendanceEntry.Value.ABSENT, "")
        for participant in session.participants.all()
    }
    with pytest.raises(ValidationError):
        submit_attendance(
            link=link, entries=entries, trainer_notes="", evidence_files=[]
        )
    client = Client()
    expired_response = client.get(reverse("attendance:trainer", args=[token]))
    guessed_response = client.get(reverse("attendance:trainer", args=["x" * 43]))
    assert expired_response.status_code == guessed_response.status_code == 410
    assert [template.name for template in expired_response.templates] == [
        template.name for template in guessed_response.templates
    ]
    assert expired_response.headers["Referrer-Policy"] == "same-origin"


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_other_manager_cannot_create_or_discover_sessions() -> None:
    manager, _supervisor, course, trainer = setup_course()
    assert manager.department is not None
    other = role_user("other-attendance-manager", "project_manager", manager.department)
    with pytest.raises(PermissionDenied):
        create_sessions(
            actor=other,
            course=course,
            trainer=trainer,
            title_ar="غير مصرح",
            title_en="Unauthorized",
            start_at=datetime(2026, 8, 6, 9, tzinfo=UTC),
            end_at=datetime(2026, 8, 6, 10, tzinfo=UTC),
        )
