"""Transactional Phase 9 scheduling, capability, and submission services."""

import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.attendance.models import (
    AttendanceEntry,
    AttendanceEvidence,
    AttendanceSubmission,
    Session,
    SessionParticipant,
    TrainerLink,
)
from apps.attendance.policies import (
    EVIDENCE_TYPES,
    MAX_EVIDENCE_FILES,
    MAX_EVIDENCE_SIZE,
    MAX_LINK_HOURS,
    MAX_RECURRENCE_COUNT,
    MIN_LINK_HOURS,
)
from apps.attendance.selectors import can_manage_session
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.courses.models import Course, CourseTrainerAssignment, Trainer
from apps.trainees.models import CourseEnrollment


def _audit(
    *,
    actor: User | None,
    action: str,
    session: Session,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="session",
        target_id=str(session.pk),
        target_label=str(session),
        metadata=metadata,
        request=request,
        scope=AuditEvent.Scope.ATTENDANCE,
    )


def _validate_session(session: Session) -> None:
    course = session.course
    if course.is_archived or course.project.is_archived:
        raise ValidationError(_("Archived courses cannot contain sessions."))
    if course.status == Course.Status.COMPLETED:
        raise ValidationError(_("Completed courses cannot contain sessions."))
    if session.start_at < course.start_at or session.end_at > course.end_at:
        raise ValidationError(_("Session time must be inside the course schedule."))
    if session.end_at <= session.start_at:
        raise ValidationError(_("Session end must be after its start."))
    if not CourseTrainerAssignment.objects.filter(
        course=course,
        trainer=session.trainer,
        removed_at__isnull=True,
        trainer__is_archived=False,
    ).exists():
        raise ValidationError(_("Select an active trainer assigned to this course."))


@transaction.atomic
def create_sessions(
    *,
    actor: User,
    course: Course,
    trainer: Trainer,
    title_ar: str,
    title_en: str,
    start_at: datetime,
    end_at: datetime,
    notes: str = "",
    recurrence: str = Session.Recurrence.NONE,
    recurrence_count: int = 1,
    request: HttpRequest | None = None,
) -> list[Session]:
    course = (
        Course.objects.select_for_update().select_related("project").get(pk=course.pk)
    )
    if not can_manage_session(actor):
        raise PermissionDenied(_("Session management permission is required."))
    if not (
        actor.has_perm("attendance.manage_all_sessions")
        or course.project.manager_id == actor.pk
    ):
        raise PermissionDenied(_("Sessions may be created only in managed courses."))
    if recurrence not in Session.Recurrence.values:
        raise ValidationError(_("Invalid recurrence choice."))
    if recurrence == Session.Recurrence.NONE:
        recurrence_count = 1
    if recurrence_count < 1 or recurrence_count > MAX_RECURRENCE_COUNT:
        raise ValidationError(_("Recurrence count must be between 1 and 52."))
    step = timedelta()
    if recurrence == Session.Recurrence.DAILY:
        step = timedelta(days=1)
    elif recurrence == Session.Recurrence.WEEKLY:
        step = timedelta(weeks=1)
    existing_source = Session.objects.filter(
        course=course,
        trainer=trainer,
        start_at=start_at,
        title_ar=title_ar.strip(),
        title_en=title_en.strip(),
    ).first()
    if existing_source is not None:
        existing_group = list(
            Session.objects.filter(
                models.Q(pk=existing_source.pk)
                | models.Q(recurrence_source=existing_source)
            ).order_by("occurrence_index")
        )
        if len(existing_group) == recurrence_count:
            return existing_group
        raise ValidationError(_("A session already exists at this start time."))
    sessions: list[Session] = []
    source: Session | None = None
    for index in range(1, recurrence_count + 1):
        session = Session(
            course=course,
            trainer=trainer,
            title_ar=title_ar.strip(),
            title_en=title_en.strip(),
            start_at=start_at + step * (index - 1),
            end_at=end_at + step * (index - 1),
            notes=notes.strip(),
            recurrence_source=source if index > 1 else None,
            occurrence_index=index,
            created_by=actor,
            updated_by=actor,
        )
        _validate_session(session)
        session.full_clean()
        session.save()
        if source is None:
            source = session
        sessions.append(session)
    if source and len(sessions) > 1:
        source.recurrence_source = source
        source.save(update_fields=("recurrence_source",))
    _audit(
        actor=actor,
        action=actions.SESSION_CREATED,
        session=sessions[0],
        metadata={"occurrences": len(sessions), "recurrence": recurrence},
        request=request,
    )
    return sessions


@transaction.atomic
def archive_session(
    *,
    actor: User,
    session: Session,
    request: HttpRequest | None = None,
) -> Session:
    session = (
        Session.objects.select_for_update()
        .select_related("course__project")
        .get(pk=session.pk)
    )
    if not actor.has_perm("attendance.archive_session") or not can_manage_session(
        actor, session
    ):
        raise PermissionDenied(_("Session archive permission is required."))
    if hasattr(session, "attendance_submission"):
        raise ValidationError(_("Submitted sessions cannot be archived."))
    session.is_archived = True
    session.archived_at = timezone.now()
    session.archived_by = actor
    session.save(update_fields=("is_archived", "archived_at", "archived_by"))
    TrainerLink.objects.filter(session=session, state=TrainerLink.State.ACTIVE).update(
        state=TrainerLink.State.REVOKED, revoked_at=timezone.now()
    )
    _audit(
        actor=actor,
        action=actions.SESSION_ARCHIVED,
        session=session,
        request=request,
    )
    return session


@transaction.atomic
def issue_trainer_link(
    *,
    actor: User,
    session: Session,
    lifetime_hours: int,
    request: HttpRequest | None = None,
) -> tuple[TrainerLink, str]:
    session = (
        Session.objects.select_for_update()
        .select_related("course__project", "trainer")
        .get(pk=session.pk)
    )
    if (
        not actor.has_perm("attendance.issue_trainer_link")
        or not can_manage_session(actor, session)
        or session.is_archived
    ):
        raise PermissionDenied(_("Trainer link issue permission is required."))
    if hasattr(session, "attendance_submission"):
        raise ValidationError(_("Attendance has already been submitted."))
    if lifetime_hours < MIN_LINK_HOURS or lifetime_hours > MAX_LINK_HOURS:
        raise ValidationError(_("Link lifetime must be between 1 hour and 14 days."))
    enrollments = list(
        CourseEnrollment.objects.filter(
            course=session.course, is_archived=False
        ).order_by("trainee_number")
    )
    if not enrollments:
        raise ValidationError(_("The session has no active trainees."))
    if len(enrollments) > session.course.capacity:
        raise ValidationError(_("Course capacity would be exceeded."))
    participants = list(session.participants.all())
    if participants:
        existing_ids = {item.enrollment_id for item in participants}
        if existing_ids != {item.pk for item in enrollments}:
            raise ValidationError(_("The session roster is already locked."))
    else:
        SessionParticipant.objects.bulk_create(
            [
                SessionParticipant(session=session, enrollment=enrollment)
                for enrollment in enrollments
            ]
        )
    now = timezone.now()
    TrainerLink.objects.filter(session=session, state=TrainerLink.State.ACTIVE).update(
        state=TrainerLink.State.REVOKED, revoked_at=now
    )
    raw_token = secrets.token_urlsafe(32)
    link = TrainerLink.objects.create(
        session=session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=now + timedelta(hours=lifetime_hours),
        issued_by=actor,
    )
    _audit(
        actor=actor,
        action=actions.TRAINER_LINK_ISSUED,
        session=session,
        metadata={"expires_at": link.expires_at.isoformat()},
        request=request,
    )
    return link, raw_token


def validate_evidence(upload: UploadedFile) -> tuple[str, bytes]:
    filename = upload.name or ""
    size = upload.size or 0
    suffix = Path(filename).suffix.lower()
    if suffix not in EVIDENCE_TYPES:
        raise ValidationError(_("Only PDF, PNG, and JPEG evidence is allowed."))
    if size <= 0 or size > MAX_EVIDENCE_SIZE:
        raise ValidationError(_("Evidence files must be 10 MB or smaller."))
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type != EVIDENCE_TYPES[suffix]:
        raise ValidationError(_("The evidence type does not match its extension."))
    content = upload.read(MAX_EVIDENCE_SIZE + 1)
    upload.seek(0)
    if len(content) != size:
        raise ValidationError(_("The evidence file could not be read safely."))
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValidationError(_("The PDF evidence is malformed."))
    if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationError(_("The PNG evidence is malformed."))
    if suffix in (".jpg", ".jpeg") and not content.startswith(b"\xff\xd8\xff"):
        raise ValidationError(_("The JPEG evidence is malformed."))
    return suffix, content


@transaction.atomic
def submit_attendance(
    *,
    link: TrainerLink,
    entries: dict[int, tuple[str, str]],
    trainer_notes: str,
    evidence_files: list[UploadedFile],
    request: HttpRequest | None = None,
) -> AttendanceSubmission:
    link = (
        TrainerLink.objects.select_for_update()
        .select_related("session")
        .get(pk=link.pk)
    )
    session = Session.objects.select_for_update().get(pk=link.session_id)
    now = timezone.now()
    if (
        link.state != TrainerLink.State.ACTIVE
        or link.expires_at <= now
        or session.is_archived
    ):
        raise ValidationError(_("This trainer link is invalid or expired."))
    if AttendanceSubmission.objects.filter(session=session).exists():
        raise ValidationError(_("Attendance has already been submitted."))
    participants = list(
        SessionParticipant.objects.filter(session=session).select_related(
            "enrollment__trainee"
        )
    )
    participant_ids = {item.pk for item in participants}
    if set(entries) != participant_ids:
        raise ValidationError(_("Attendance is required for every session trainee."))
    if len(evidence_files) > MAX_EVIDENCE_FILES:
        raise ValidationError(_("At most five evidence files may be uploaded."))
    prepared_files = [(upload, *validate_evidence(upload)) for upload in evidence_files]
    for value, _notes in entries.values():
        if value not in AttendanceEntry.Value.values:
            raise ValidationError(_("Select a valid attendance value."))
    submission = AttendanceSubmission.objects.create(
        session=session,
        trainer_link=link,
        trainer_notes=trainer_notes.strip(),
    )
    AttendanceEntry.objects.bulk_create(
        [
            AttendanceEntry(
                submission=submission,
                participant=participant,
                value=entries[participant.pk][0],
                notes=entries[participant.pk][1].strip(),
            )
            for participant in participants
        ]
    )
    for upload, _suffix, content in prepared_files:
        record = AttendanceEvidence(
            submission=submission,
            original_name=Path(upload.name or "").name[:255],
            size=len(content),
            content_type=upload.content_type or "application/octet-stream",
            sha256=hashlib.sha256(content).hexdigest(),
        )
        record.file.save(record.original_name, upload, save=False)
        record.save()
    link.state = TrainerLink.State.SUBMITTED
    link.save(update_fields=("state",))
    _audit(
        actor=None,
        action=actions.ATTENDANCE_SUBMITTED,
        session=session,
        metadata={"entries": len(entries), "evidence": len(evidence_files)},
        request=request,
    )
    return submission
