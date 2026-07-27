"""Transactional Phase 4 course, trainer, assignment, and file services."""

import hashlib
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.courses.models import Course, CourseFile, CourseTrainerAssignment, Trainer
from apps.courses.policies import (
    COURSE_FILE_TYPES,
    COURSE_STATUS_TRANSITIONS,
    MAX_COURSE_FILE_SIZE,
)
from apps.courses.selectors import (
    can_archive_course,
    can_manage_course,
    can_manage_course_trainers,
    can_upload_course_file,
)


def _course_event(
    *,
    actor: User,
    action: str,
    course: Course,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="course",
        target_id=str(course.pk),
        target_label=course.code,
        metadata=metadata,
        request=request,
        scope=AuditEvent.Scope.COURSES,
    )


def _validate_course(course: Course) -> None:
    project = course.project
    if project.is_archived:
        raise ValidationError(_("Archived projects cannot own editable courses."))
    if course.status == Course.Status.ACTIVE and project.status != "active":
        raise ValidationError(_("Only an active project can contain an active course."))
    local_start = timezone.localtime(course.start_at).date()
    local_end = timezone.localtime(course.end_at).date()
    if local_start < project.start_date or local_end > project.end_date:
        raise ValidationError(_("Course schedule must be inside the project dates."))
    course.full_clean()


@transaction.atomic
def create_course(
    *,
    actor: User,
    request: HttpRequest | None = None,
    **data: object,
) -> Course:
    if not actor.has_perm("courses.add_course"):
        raise PermissionDenied(_("Course creation permission is required."))
    raw_code = data.get("code")
    if isinstance(raw_code, str):
        data["code"] = raw_code.strip().upper()
    course = Course(**data, created_by=actor, updated_by=actor)
    if not (
        actor.has_perm("courses.view_all_courses")
        or course.project.manager_id == actor.pk
    ):
        raise PermissionDenied(_("Courses may be created only in managed projects."))
    if course.status != Course.Status.DRAFT:
        raise ValidationError(_("New courses must start as Draft."))
    _validate_course(course)
    course.save()
    _course_event(
        actor=actor, action=actions.COURSE_CREATED, course=course, request=request
    )
    return course


@transaction.atomic
def update_course(
    *,
    actor: User,
    course: Course,
    request: HttpRequest | None = None,
    **data: object,
) -> Course:
    course = (
        Course.objects.select_for_update().select_related("project").get(pk=course.pk)
    )
    if not can_manage_course(actor, course):
        raise PermissionDenied(_("Course update permission is required."))
    previous_status = course.status
    if data.get("code") != course.code or data.get("project") != course.project:
        raise ValidationError(_("Course code and project cannot be changed."))
    for field_name, value in data.items():
        setattr(course, field_name, value)
    if (
        course.status != previous_status
        and course.status not in COURSE_STATUS_TRANSITIONS[previous_status]
    ):
        raise ValidationError(_("This course status transition is not allowed."))
    _validate_course(course)
    course.updated_by = actor
    course.save()
    action = (
        actions.COURSE_STATUS_CHANGED
        if course.status != previous_status
        else actions.COURSE_UPDATED
    )
    _course_event(
        actor=actor,
        action=action,
        course=course,
        metadata={"previous_status": previous_status, "status": course.status},
        request=request,
    )
    return course


@transaction.atomic
def archive_course(
    *, actor: User, course: Course, request: HttpRequest | None = None
) -> Course:
    from apps.tasks.models import Task

    course = Course.objects.select_for_update().get(pk=course.pk)
    if not can_archive_course(actor, course):
        raise PermissionDenied(_("Course archive permission is required."))
    if course.is_archived:
        return course
    if Task.objects.filter(course=course, is_archived=False).exists():
        raise ValidationError(_("Archive every task before archiving this course."))
    now = timezone.now()
    CourseTrainerAssignment.objects.filter(
        course=course, removed_at__isnull=True
    ).update(removed_by=actor, removed_at=now)
    course.is_archived = True
    course.archived_at = now
    course.archived_by = actor
    course.updated_by = actor
    course.save(
        update_fields=(
            "is_archived",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        )
    )
    _course_event(
        actor=actor, action=actions.COURSE_ARCHIVED, course=course, request=request
    )
    return course


@transaction.atomic
def restore_course(
    *, actor: User, course: Course, request: HttpRequest | None = None
) -> Course:
    course = (
        Course.objects.select_for_update().select_related("project").get(pk=course.pk)
    )
    if not can_archive_course(actor, course):
        raise PermissionDenied(_("Course restore permission is required."))
    if course.project.is_archived:
        raise ValidationError(_("Restore the parent project first."))
    if not course.is_archived:
        return course
    course.is_archived = False
    course.archived_at = None
    course.archived_by = None
    course.updated_by = actor
    _validate_course(course)
    course.save(
        update_fields=(
            "is_archived",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        )
    )
    _course_event(
        actor=actor, action=actions.COURSE_RESTORED, course=course, request=request
    )
    return course


@transaction.atomic
def replace_course_trainers(
    *,
    actor: User,
    course: Course,
    trainers: Iterable[Trainer],
    request: HttpRequest | None = None,
) -> None:
    course = Course.objects.select_for_update().get(pk=course.pk)
    if not can_manage_course_trainers(actor, course):
        raise PermissionDenied(_("Course trainer permission is required."))
    trainer_list = list(trainers)
    if any(trainer.is_archived for trainer in trainer_list):
        raise ValidationError(_("Archived trainers cannot be assigned."))
    requested_ids = {trainer.pk for trainer in trainer_list}
    active = CourseTrainerAssignment.objects.select_for_update().filter(
        course=course, removed_at__isnull=True
    )
    current_ids = set(active.values_list("trainer_id", flat=True))
    now = timezone.now()
    active.exclude(trainer_id__in=requested_ids).update(
        removed_by=actor, removed_at=now
    )
    for trainer in trainer_list:
        if trainer.pk not in current_ids:
            CourseTrainerAssignment.objects.create(
                course=course, trainer=trainer, assigned_by=actor
            )
    if current_ids != requested_ids:
        _course_event(
            actor=actor,
            action=actions.COURSE_TRAINERS_UPDATED,
            course=course,
            metadata={
                "added_trainer_ids": sorted(requested_ids - current_ids),
                "removed_trainer_ids": sorted(current_ids - requested_ids),
            },
            request=request,
        )


def _trainer_event(
    *,
    actor: User,
    action: str,
    trainer: Trainer,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="trainer",
        target_id=str(trainer.pk),
        target_label=trainer.code,
        request=request,
        scope=AuditEvent.Scope.COURSES,
    )


@transaction.atomic
def save_trainer(
    *,
    actor: User,
    instance: Trainer | None = None,
    request: HttpRequest | None = None,
    **data: object,
) -> Trainer:
    permission = "courses.change_trainer" if instance else "courses.add_trainer"
    if not actor.has_perm(permission):
        raise PermissionDenied(_("Trainer administration permission is required."))
    trainer = (
        Trainer.objects.select_for_update().get(pk=instance.pk)
        if instance is not None
        else Trainer(created_by=actor)
    )
    if trainer.is_archived:
        raise ValidationError(_("Archived trainers are read-only."))
    if instance is not None and data.get("code") != trainer.code:
        raise ValidationError(_("Trainer codes cannot be changed."))
    for field_name, value in data.items():
        setattr(trainer, field_name, value)
    trainer.updated_by = actor
    trainer.full_clean()
    trainer.save()
    _trainer_event(
        actor=actor,
        action=actions.TRAINER_UPDATED if instance else actions.TRAINER_CREATED,
        trainer=trainer,
        request=request,
    )
    return trainer


@transaction.atomic
def set_trainer_archived(
    *,
    actor: User,
    trainer: Trainer,
    archived: bool,
    request: HttpRequest | None = None,
) -> Trainer:
    permission = "courses.archive_trainer" if archived else "courses.restore_trainer"
    if not actor.has_perm(permission):
        raise PermissionDenied(_("Trainer archive permission is required."))
    trainer = Trainer.objects.select_for_update().get(pk=trainer.pk)
    if archived and trainer.course_assignments.filter(removed_at__isnull=True).exists():
        raise ValidationError(_("Active course assignments still use this trainer."))
    trainer.is_archived = archived
    trainer.archived_at = timezone.now() if archived else None
    trainer.archived_by = actor if archived else None
    trainer.updated_by = actor
    trainer.save(
        update_fields=(
            "is_archived",
            "archived_at",
            "archived_by",
            "updated_by",
            "updated_at",
        )
    )
    _trainer_event(
        actor=actor,
        action=actions.TRAINER_ARCHIVED if archived else actions.TRAINER_RESTORED,
        trainer=trainer,
        request=request,
    )
    return trainer


def _read_all(upload: UploadedFile) -> bytes:
    upload.seek(0)
    data = cast(bytes, upload.read())
    upload.seek(0)
    return data


def validate_course_file(upload: UploadedFile) -> tuple[str, bytes]:
    """Validate extension, declared MIME, size, and file structure."""
    upload_name = upload.name or ""
    upload_size = upload.size or 0
    suffix = Path(upload_name).suffix.lower()
    expected_type = COURSE_FILE_TYPES.get(suffix)
    if expected_type is None:
        raise ValidationError(_("This file type is not allowed."))
    if upload_size > MAX_COURSE_FILE_SIZE:
        raise ValidationError(_("Course files cannot exceed 25 MiB."))
    if upload.content_type != expected_type:
        raise ValidationError(_("The declared file type does not match its extension."))
    data = _read_all(upload)
    valid = False
    if suffix == ".pdf":
        valid = data.startswith(b"%PDF-")
    elif suffix == ".png":
        valid = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif suffix in {".jpg", ".jpeg"}:
        valid = data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
    else:
        required = {
            ".docx": "word/document.xml",
            ".xlsx": "xl/workbook.xml",
            ".pptx": "ppt/presentation.xml",
        }[suffix]
        try:
            with zipfile.ZipFile(upload) as archive:
                valid = required in archive.namelist()
        except (OSError, zipfile.BadZipFile):
            valid = False
        finally:
            upload.seek(0)
    if not valid:
        raise ValidationError(_("The file content does not match the allowed type."))
    return expected_type, data


@transaction.atomic
def upload_course_file(
    *,
    actor: User,
    course: Course,
    upload: UploadedFile,
    request: HttpRequest | None = None,
) -> CourseFile:
    course = Course.objects.select_for_update().get(pk=course.pk)
    if not can_upload_course_file(actor, course):
        raise PermissionDenied(_("Course file upload permission is required."))
    content_type, data = validate_course_file(upload)
    record = CourseFile(
        course=course,
        file=upload,
        original_name=Path(upload.name or "").name[:255],
        size=upload.size or 0,
        content_type=content_type,
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=actor,
    )
    record.full_clean()
    record.save()
    _course_event(
        actor=actor,
        action=actions.COURSE_FILE_UPLOADED,
        course=course,
        metadata={
            "file_id": record.pk,
            "name": record.original_name,
            "size": record.size,
        },
        request=request,
    )
    return record
