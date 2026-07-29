"""Transactional Phase 5 task and collaboration services."""

import hashlib
import zipfile
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.projects.models import Project
from apps.tasks.models import (
    Tag,
    Task,
    TaskAssignment,
    TaskComment,
    TaskFile,
    TaskTag,
)
from apps.tasks.policies import (
    MAX_TASK_FILE_SIZE,
    TASK_FILE_TYPES,
    TASK_STATUS_TRANSITIONS,
)
from apps.tasks.selectors import (
    can_archive_task,
    can_manage_task,
    can_restore_task,
    can_update_assigned_task,
    task_manager_id,
    tasks_visible_to,
)


def _task_event(
    *,
    actor: User,
    action: str,
    task: Task,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="task",
        target_id=str(task.pk),
        target_label=task.code,
        metadata=metadata,
        request=request,
        scope=AuditEvent.Scope.TASKS,
    )


def owner_project(task: Task) -> Project:
    if task.project_id:
        project = task.project
        assert project is not None
        return project
    course = task.course
    assert course is not None
    return course.project


def eligible_task_users(task: Task) -> Q:
    project = owner_project(task)
    return (
        Q(pk=project.manager_id)
        | Q(pk=project.supervisor_id)
        | Q(
            project_memberships__project=project,
            project_memberships__removed_at__isnull=True,
        )
    )


def _validate_task(task: Task) -> None:
    project = owner_project(task)
    if project.is_archived:
        raise ValidationError(_("Archived contexts cannot own editable tasks."))
    course = task.course
    if task.course_id:
        assert course is not None
        if course.is_archived:
            raise ValidationError(_("Archived courses cannot own editable tasks."))
    if task.start_date and task.start_date < project.start_date:
        raise ValidationError(_("Task dates must be inside the owner dates."))
    if task.due_date and task.due_date > project.end_date:
        raise ValidationError(_("Task dates must be inside the owner dates."))
    if task.course_id:
        assert course is not None
        start_date = timezone.localtime(course.start_at).date()
        end_date = timezone.localtime(course.end_at).date()
        if task.start_date and task.start_date < start_date:
            raise ValidationError(_("Task dates must be inside the course schedule."))
        if task.due_date and task.due_date > end_date:
            raise ValidationError(_("Task dates must be inside the course schedule."))
    task.full_clean()


def _validate_assignees(
    task: Task,
    assignees: Iterable[User],
    primary_owner: User,
) -> list[User]:
    users = list(assignees)
    if primary_owner not in users:
        raise ValidationError(_("Primary owner must be an assignee."))
    eligible_ids = set(
        User.objects.filter(is_active=True)
        .filter(eligible_task_users(task))
        .values_list("pk", flat=True)
    )
    if any(user.pk not in eligible_ids for user in users):
        raise ValidationError(_("Every assignee must be eligible and active."))
    return users


@transaction.atomic
def create_task(
    *,
    actor: User,
    assignees: Iterable[User],
    primary_owner: User,
    request: HttpRequest | None = None,
    **data: object,
) -> Task:
    if not actor.has_perm("tasks.add_task"):
        raise PermissionDenied(_("Task creation permission is required."))
    raw_code = data.get("code")
    if isinstance(raw_code, str):
        data["code"] = raw_code.strip().upper()
    task = Task(**data, created_by=actor, updated_by=actor)
    if not (
        actor.has_perm("tasks.view_all_tasks") or task_manager_id(task) == actor.pk
    ):
        raise PermissionDenied(_("Tasks may be created only in managed contexts."))
    if task.status != Task.Status.TODO:
        raise ValidationError(_("New tasks must start as To Do."))
    _validate_task(task)
    users = _validate_assignees(task, assignees, primary_owner)
    task.save()
    for user in users:
        TaskAssignment.objects.create(
            task=task,
            user=user,
            is_primary=user.pk == primary_owner.pk,
            assigned_by=actor,
        )
    _task_event(actor=actor, action=actions.TASK_CREATED, task=task, request=request)
    return task


@transaction.atomic
def update_task(
    *,
    actor: User,
    task: Task,
    request: HttpRequest | None = None,
    **data: object,
) -> Task:
    task = (
        Task.objects.select_for_update()
        .select_related("project", "course", "course__project", "parent")
        .get(pk=task.pk)
    )
    from apps.approvals.services import has_pending_approval

    if has_pending_approval(task):
        raise ValidationError(_("Pending approval prevents task changes."))
    if not can_manage_task(actor, task):
        raise PermissionDenied(_("Task update permission is required."))
    previous_status = task.status
    if (
        data.get("code") != task.code
        or data.get("project") != task.project
        or data.get("course") != task.course
    ):
        raise ValidationError(_("Task code and owner context cannot be changed."))
    for field_name, value in data.items():
        setattr(task, field_name, value)
    if (
        task.status != previous_status
        and task.status not in TASK_STATUS_TRANSITIONS[previous_status]
    ):
        raise ValidationError(_("This task status transition is not allowed."))
    _validate_task(task)
    task.updated_by = actor
    task.save()
    _task_event(
        actor=actor,
        action=(
            actions.TASK_STATUS_CHANGED
            if task.status != previous_status
            else actions.TASK_UPDATED
        ),
        task=task,
        metadata={"previous_status": previous_status, "status": task.status},
        request=request,
    )
    return task


@transaction.atomic
def update_assigned_task(
    *,
    actor: User,
    task: Task,
    status: str,
    actual_hours: Decimal | None,
    blocking_reason: str,
    request: HttpRequest | None = None,
) -> Task:
    task = Task.objects.select_for_update().get(pk=task.pk)
    from apps.approvals.services import has_pending_approval

    if has_pending_approval(task):
        raise ValidationError(_("Pending approval prevents task changes."))
    if not can_update_assigned_task(actor, task):
        raise PermissionDenied(_("Assigned-task update permission is required."))
    previous_status = task.status
    if (
        status != previous_status
        and status not in TASK_STATUS_TRANSITIONS[previous_status]
    ):
        raise ValidationError(_("This task status transition is not allowed."))
    task.status = status
    task.actual_hours = actual_hours
    task.blocking_reason = blocking_reason
    _validate_task(task)
    task.updated_by = actor
    task.save()
    _task_event(
        actor=actor,
        action=actions.TASK_STATUS_CHANGED,
        task=task,
        metadata={"previous_status": previous_status, "status": task.status},
        request=request,
    )
    return task


@transaction.atomic
def replace_task_assignments(
    *,
    actor: User,
    task: Task,
    assignees: Iterable[User],
    primary_owner: User,
    request: HttpRequest | None = None,
) -> None:
    task = Task.objects.select_for_update().get(pk=task.pk)
    from apps.approvals.services import has_pending_approval

    if has_pending_approval(task):
        raise ValidationError(_("Pending approval prevents task archiving."))
    if not (
        actor.has_perm("tasks.manage_task_assignments") and can_manage_task(actor, task)
    ):
        raise PermissionDenied(_("Task assignment permission is required."))
    users = _validate_assignees(task, assignees, primary_owner)
    requested = {user.pk for user in users}
    active = TaskAssignment.objects.select_for_update().filter(
        task=task, removed_at__isnull=True
    )
    now = timezone.now()
    active.exclude(user_id__in=requested).update(removed_by=actor, removed_at=now)
    active.filter(user_id__in=requested).update(is_primary=False)
    for user in users:
        assignment = active.filter(user=user).first()
        if assignment:
            assignment.is_primary = user.pk == primary_owner.pk
            assignment.save(update_fields=("is_primary",))
        else:
            TaskAssignment.objects.create(
                task=task,
                user=user,
                is_primary=user.pk == primary_owner.pk,
                assigned_by=actor,
            )
    _task_event(
        actor=actor,
        action=actions.TASK_ASSIGNMENTS_UPDATED,
        task=task,
        request=request,
    )


@transaction.atomic
def archive_task(
    *, actor: User, task: Task, request: HttpRequest | None = None
) -> Task:
    task = Task.objects.select_for_update().get(pk=task.pk)
    if not can_archive_task(actor, task):
        raise PermissionDenied(_("Task archive permission is required."))
    if task.subtasks.filter(is_archived=False).exists():
        raise ValidationError(_("Archive subtasks before archiving their parent."))
    if task.is_archived:
        return task
    now = timezone.now()
    TaskAssignment.objects.filter(task=task, removed_at__isnull=True).update(
        removed_by=actor, removed_at=now
    )
    TaskTag.objects.filter(task=task, removed_at__isnull=True).update(
        removed_by=actor, removed_at=now
    )
    task.is_archived = True
    task.archived_at = now
    task.archived_by = actor
    task.updated_by = actor
    task.save()
    _task_event(actor=actor, action=actions.TASK_ARCHIVED, task=task, request=request)
    return task


@transaction.atomic
def restore_task(
    *, actor: User, task: Task, request: HttpRequest | None = None
) -> Task:
    task = Task.objects.select_for_update().get(pk=task.pk)
    if not can_restore_task(actor, task):
        raise PermissionDenied(_("Task restore permission is required."))
    if not task.is_archived:
        return task
    if task.parent and task.parent.is_archived:
        raise ValidationError(_("Restore the parent task first."))
    previous = list(
        TaskAssignment.objects.select_for_update()
        .select_related("user")
        .filter(task=task, removed_at__isnull=False)
        .order_by("-removed_at", "pk")
    )
    if not previous:
        raise ValidationError(_("Assign an eligible primary owner before restoring."))
    latest_removed_at = previous[0].removed_at
    previous = [
        assignment
        for assignment in previous
        if assignment.removed_at == latest_removed_at
    ]
    primary = next(
        (assignment.user for assignment in previous if assignment.is_primary),
        None,
    )
    if primary is None:
        raise ValidationError(_("Assign an eligible primary owner before restoring."))
    users = _validate_assignees(
        task,
        (assignment.user for assignment in previous),
        primary,
    )
    task.is_archived = False
    task.archived_at = None
    task.archived_by = None
    task.updated_by = actor
    _validate_task(task)
    task.save()
    for user in users:
        TaskAssignment.objects.create(
            task=task,
            user=user,
            is_primary=user.pk == primary.pk,
            assigned_by=actor,
        )
    _task_event(actor=actor, action=actions.TASK_RESTORED, task=task, request=request)
    return task


@transaction.atomic
def add_task_comment(
    *,
    actor: User,
    task: Task,
    body: str,
    request: HttpRequest | None = None,
) -> TaskComment:
    if (
        not actor.has_perm("tasks.comment_task")
        or not tasks_visible_to(actor).filter(pk=task.pk).exists()
    ):
        raise PermissionDenied(_("Task comment permission is required."))
    if task.is_archived:
        raise ValidationError(_("Archived tasks are read-only."))
    comment = TaskComment(task=task, author=actor, body=body)
    comment.full_clean()
    comment.save()
    _task_event(
        actor=actor,
        action=actions.TASK_COMMENT_ADDED,
        task=task,
        metadata={"comment_id": comment.pk},
        request=request,
    )
    return comment


@transaction.atomic
def replace_task_tags(
    *,
    actor: User,
    task: Task,
    tags: Iterable[Tag],
    request: HttpRequest | None = None,
) -> None:
    if not can_manage_task(actor, task):
        raise PermissionDenied(_("Task tag permission is required."))
    tag_list = list(tags)
    if any(tag.is_archived for tag in tag_list):
        raise ValidationError(_("Archived tags cannot be assigned."))
    requested = {tag.pk for tag in tag_list}
    active = TaskTag.objects.select_for_update().filter(
        task=task, removed_at__isnull=True
    )
    now = timezone.now()
    active.exclude(tag_id__in=requested).update(removed_by=actor, removed_at=now)
    current = set(active.values_list("tag_id", flat=True))
    for tag in tag_list:
        if tag.pk not in current:
            TaskTag.objects.create(task=task, tag=tag, added_by=actor)
    _task_event(
        actor=actor, action=actions.TASK_TAGS_UPDATED, task=task, request=request
    )


@transaction.atomic
def save_tag(
    *,
    actor: User,
    code: str,
    name_ar: str,
    name_en: str,
    instance: Tag | None = None,
    request: HttpRequest | None = None,
) -> Tag:
    permission = "tasks.change_tag" if instance else "tasks.add_tag"
    if not actor.has_perm(permission):
        raise PermissionDenied(_("Tag administration permission is required."))
    tag = (
        Tag.objects.select_for_update().get(pk=instance.pk)
        if instance is not None
        else Tag(created_by=actor)
    )
    if tag.is_archived:
        raise ValidationError(_("Archived tags are read-only."))
    if instance and code.strip().upper() != tag.code:
        raise ValidationError(_("Tag codes cannot be changed."))
    tag.code = code
    tag.name_ar = name_ar
    tag.name_en = name_en
    tag.updated_by = actor
    tag.full_clean()
    tag.save()
    record_audit_event(
        actor=actor,
        action=actions.TAG_UPDATED if instance else actions.TAG_CREATED,
        target_type="tag",
        target_id=str(tag.pk),
        target_label=tag.code,
        request=request,
        scope=AuditEvent.Scope.TASKS,
    )
    return tag


@transaction.atomic
def set_tag_archived(
    *,
    actor: User,
    tag: Tag,
    archived: bool,
    request: HttpRequest | None = None,
) -> Tag:
    permission = "tasks.archive_tag" if archived else "tasks.restore_tag"
    if not actor.has_perm(permission):
        raise PermissionDenied(_("Tag archive permission is required."))
    tag = Tag.objects.select_for_update().get(pk=tag.pk)
    if archived and tag.task_links.filter(removed_at__isnull=True).exists():
        raise ValidationError(_("Active tasks still use this tag."))
    tag.is_archived = archived
    tag.archived_at = timezone.now() if archived else None
    tag.updated_by = actor
    tag.save(update_fields=("is_archived", "archived_at", "updated_by", "updated_at"))
    record_audit_event(
        actor=actor,
        action=actions.TAG_ARCHIVED if archived else actions.TAG_RESTORED,
        target_type="tag",
        target_id=str(tag.pk),
        target_label=tag.code,
        request=request,
        scope=AuditEvent.Scope.TASKS,
    )
    return tag


def _read_all(upload: UploadedFile) -> bytes:
    upload.seek(0)
    data = cast(bytes, upload.read())
    upload.seek(0)
    return data


def validate_task_file(upload: UploadedFile) -> tuple[str, bytes]:
    suffix = Path(upload.name or "").suffix.lower()
    expected = TASK_FILE_TYPES.get(suffix)
    if expected is None:
        raise ValidationError(_("This file type is not allowed."))
    if (upload.size or 0) > MAX_TASK_FILE_SIZE:
        raise ValidationError(_("Task files cannot exceed 25 MiB."))
    if upload.content_type != expected:
        raise ValidationError(_("The declared file type does not match its extension."))
    data = _read_all(upload)
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
    return expected, data


@transaction.atomic
def upload_task_file(
    *,
    actor: User,
    task: Task,
    upload: UploadedFile,
    request: HttpRequest | None = None,
) -> TaskFile:
    if (
        not actor.has_perm("tasks.upload_task_file")
        or not tasks_visible_to(actor).filter(pk=task.pk).exists()
    ):
        raise PermissionDenied(_("Task file upload permission is required."))
    if task.is_archived:
        raise ValidationError(_("Archived tasks are read-only."))
    content_type, data = validate_task_file(upload)
    record = TaskFile(
        task=task,
        file=upload,
        original_name=Path(upload.name or "").name[:255],
        size=upload.size or 0,
        content_type=content_type,
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by=actor,
    )
    record.full_clean()
    record.save()
    _task_event(
        actor=actor,
        action=actions.TASK_FILE_UPLOADED,
        task=task,
        metadata={"file_id": record.pk, "name": record.original_name},
        request=request,
    )
    return record
