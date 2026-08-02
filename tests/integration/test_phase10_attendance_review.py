"""Phase 10 review, reopening, correction, and authorization tests."""

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
    AttendanceCorrection,
    AttendanceEntry,
    AttendanceReview,
    AttendanceSubmission,
    TrainerLink,
)
from apps.attendance.services import (
    correct_attendance,
    issue_trainer_link,
    review_attendance,
    submit_attendance,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from tests.integration.test_phase9_attendance import (
    create_one_session,
    role_user,
    setup_course,
)

PHASE10_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    import_module(
        "apps.attendance.migrations.0005_seed_phase10_permissions"
    ).ROLE_PERMISSIONS,
)


def create_submission() -> tuple[User, User, AttendanceSubmission, TrainerLink, str]:
    manager, supervisor, course, trainer = setup_course()
    session = create_one_session(manager, course, trainer)
    link, token = issue_trainer_link(actor=manager, session=session, lifetime_hours=1)
    entries: dict[int, tuple[str, str]] = {
        participant.pk: (str(AttendanceEntry.Value.PRESENT), "")
        for participant in session.participants.all()
    }
    submission = submit_attendance(
        link=link,
        entries=entries,
        trainer_notes="ملاحظة المدرب",
        evidence_files=[],
    )
    return manager, supervisor, submission, link, token


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_phase10_permissions_match_approved_additions() -> None:
    for role_code, expected in PHASE10_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="attendance"
            )
        }
        assert expected <= actual


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_reject_reopens_same_link_resubmit_and_approve_read_only() -> None:
    _manager, supervisor, submission, link, token = create_submission()
    token_hash = link.token_hash
    rejected = review_attendance(
        actor=supervisor,
        submission=submission,
        decision=AttendanceReview.Decision.REJECTED,
        reason="يرجى تصحيح حالة المتدرب",
    )
    link.refresh_from_db()
    assert rejected.state == AttendanceSubmission.State.REJECTED
    assert link.state == TrainerLink.State.ACTIVE
    assert link.token_hash == token_hash
    assert 71.9 < (link.expires_at - timezone.now()).total_seconds() / 3600 <= 72
    assert rejected.reviews.get().reason == "يرجى تصحيح حالة المتدرب"

    client = Client()
    reopened = client.get(reverse("attendance:trainer", args=[token]))
    assert reopened.status_code == 200
    assert "يرجى تصحيح حالة المتدرب" in reopened.content.decode()

    entries: dict[int, tuple[str, str]] = {
        entry.participant_id: (
            str(AttendanceEntry.Value.LATE)
            if index == 0
            else str(AttendanceEntry.Value.PRESENT),
            "تم التصحيح" if index == 0 else "",
        )
        for index, entry in enumerate(submission.entries.order_by("participant_id"))
    }
    resubmitted = submit_attendance(
        link=link,
        entries=entries,
        trainer_notes="أعيد الإرسال",
        evidence_files=[],
    )
    assert resubmitted.pk == submission.pk
    assert resubmitted.state == AttendanceSubmission.State.PENDING_REVIEW
    assert resubmitted.reviews.count() == 1

    approved = review_attendance(
        actor=supervisor,
        submission=resubmitted,
        decision=AttendanceReview.Decision.APPROVED,
    )
    assert approved.state == AttendanceSubmission.State.APPROVED
    assert list(approved.reviews.values_list("attempt", flat=True)) == [1, 2]
    read_only = client.get(reverse("attendance:trainer", args=[token]))
    assert read_only.status_code == 200
    assert "attendance/trainer_read_only.html" in {
        template.name for template in read_only.templates
    }
    assert b'type="radio"' not in read_only.content
    assert not AuditEvent.objects.filter(metadata__icontains=token).exists()
    assert AuditEvent.objects.filter(action=actions.ATTENDANCE_REJECTED).exists()
    assert AuditEvent.objects.filter(action=actions.ATTENDANCE_RESUBMITTED).exists()
    assert AuditEvent.objects.filter(action=actions.ATTENDANCE_APPROVED).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_review_and_correction_are_scoped_reasoned_and_immutable() -> None:
    manager, supervisor, submission, _link, _token = create_submission()
    assert manager.department is not None
    other_supervisor = role_user(
        "wrong-attendance-supervisor", "supervisor", manager.department
    )
    with pytest.raises(PermissionDenied):
        review_attendance(
            actor=other_supervisor,
            submission=submission,
            decision=AttendanceReview.Decision.APPROVED,
        )
    with pytest.raises(ValidationError):
        review_attendance(
            actor=supervisor,
            submission=submission,
            decision=AttendanceReview.Decision.REJECTED,
            reason=" ",
        )
    review_attendance(
        actor=supervisor,
        submission=submission,
        decision=AttendanceReview.Decision.APPROVED,
    )
    with pytest.raises(PermissionDenied):
        correct_attendance(
            actor=supervisor,
            submission=submission,
            entries={
                entry.participant_id: (entry.value, entry.notes)
                for entry in submission.entries.all()
            },
            reason="غير مصرح",
        )
    entries: dict[int, tuple[str, str]] = {
        entry.participant_id: (
            str(AttendanceEntry.Value.EXCUSED) if index == 0 else entry.value,
            "سبب موثق" if index == 0 else entry.notes,
        )
        for index, entry in enumerate(submission.entries.order_by("participant_id"))
    }
    correction = correct_attendance(
        actor=manager,
        submission=submission,
        entries=entries,
        reason="تصحيح بناءً على السجل الرسمي",
    )
    submission.refresh_from_db()
    assert submission.state == AttendanceSubmission.State.APPROVED
    assert correction.before_snapshot != correction.after_snapshot
    assert AttendanceCorrection.objects.count() == 1
    assert AuditEvent.objects.filter(action=actions.ATTENDANCE_CORRECTED).exists()
    correction.reason = "mutated"
    with pytest.raises(PermissionDenied):
        correction.save()
    with pytest.raises(PermissionDenied):
        AttendanceCorrection.objects.filter(pk=correction.pk).update(reason="mutated")
    with pytest.raises(PermissionDenied):
        correction.delete()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_personal_attendance_scope_hides_other_projects_and_employees() -> None:
    manager, supervisor, submission, _link, _token = create_submission()
    assert manager.department is not None
    employee = role_user("attendance-employee", "employee", manager.department)
    other_manager = role_user(
        "attendance-other-manager", "project_manager", manager.department
    )
    client = Client()
    client.force_login(supervisor)
    assert client.get(reverse("attendance:review-queue")).status_code == 200
    assert (
        client.get(
            reverse("attendance:submission-detail", args=[submission.pk])
        ).status_code
        == 200
    )
    client.force_login(other_manager)
    assert (
        client.get(
            reverse("attendance:submission-detail", args=[submission.pk])
        ).status_code
        == 404
    )
    client.force_login(employee)
    assert (
        client.get(
            reverse("attendance:submission-detail", args=[submission.pk])
        ).status_code
        == 404
    )
