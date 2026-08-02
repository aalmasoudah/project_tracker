"""Permission- and object-scoped archive and operations selectors."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final, cast

from django.db import models
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.approvals.selectors import milestones_visible_to
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.courses.selectors import courses_visible_to, trainers_visible_to
from apps.operations.policies import RESTORE_TEST_INTERVAL_DAYS, RPO_HOURS
from apps.organizations.selectors import departments_visible_to
from apps.projects.models import Category, Client, Project
from apps.projects.selectors import projects_visible_to
from apps.tasks.models import Tag
from apps.tasks.selectors import tasks_visible_to
from apps.trainees.models import CourseEnrollment
from apps.trainees.selectors import enrollments_visible_to


@dataclass(frozen=True)
class ArchiveTypeDefinition:
    code: str
    label: object
    permission: str


@dataclass(frozen=True)
class ArchiveEntry:
    type_code: str
    type_label: object
    code: str
    label: str
    archived_at: datetime
    restore_url: str


@dataclass(frozen=True)
class RecordedStatus:
    state: str
    completed_at: datetime | None = None
    environment: str = ""
    result: str = ""


ARCHIVE_TYPE_DEFINITIONS: Final = (
    ArchiveTypeDefinition(
        "department",
        _("Departments"),
        "organizations.restore_department",
    ),
    ArchiveTypeDefinition("client", _("Clients"), "projects.restore_client"),
    ArchiveTypeDefinition(
        "category",
        _("Categories"),
        "projects.restore_category",
    ),
    ArchiveTypeDefinition("project", _("Projects"), "projects.restore_project"),
    ArchiveTypeDefinition("trainer", _("Trainers"), "courses.restore_trainer"),
    ArchiveTypeDefinition("course", _("Courses"), "courses.restore_course"),
    ArchiveTypeDefinition("tag", _("Tags"), "tasks.restore_tag"),
    ArchiveTypeDefinition("task", _("Tasks"), "tasks.restore_task"),
    ArchiveTypeDefinition(
        "milestone",
        _("Milestones"),
        "approvals.restore_milestone",
    ),
    ArchiveTypeDefinition(
        "enrollment",
        _("Trainee enrollments"),
        "trainees.restore_enrollment",
    ),
)
ARCHIVE_TYPE_BY_CODE: Final = {
    definition.code: definition for definition in ARCHIVE_TYPE_DEFINITIONS
}


def archive_types_available_to(actor: User) -> tuple[ArchiveTypeDefinition, ...]:
    if not actor.has_perm("operations.view_archive_center"):
        return ()
    return tuple(
        definition
        for definition in ARCHIVE_TYPE_DEFINITIONS
        if actor.has_perm(definition.permission)
    )


def archived_records_visible_to(
    actor: User,
    record_type: str,
    *,
    query: str = "",
) -> QuerySet[models.Model]:
    available = {item.code for item in archive_types_available_to(actor)}
    if record_type not in available:
        return cast(QuerySet[models.Model], Project.objects.none())
    records: QuerySet[Any]
    normalized = normalize_account_search(query)
    if record_type == "department":
        records = departments_visible_to(actor).filter(is_archived=True)
    elif record_type == "client":
        records = Client.objects.filter(is_archived=True)
    elif record_type == "category":
        records = Category.objects.filter(is_archived=True)
    elif record_type == "project":
        records = projects_visible_to(actor, include_archived=True).filter(
            is_archived=True
        )
    elif record_type == "trainer":
        records = trainers_visible_to(actor).filter(is_archived=True)
    elif record_type == "course":
        records = courses_visible_to(actor, include_archived=True).filter(
            is_archived=True
        )
    elif record_type == "tag":
        records = Tag.objects.filter(is_archived=True)
    elif record_type == "task":
        records = tasks_visible_to(actor, include_archived=True).filter(
            is_archived=True
        )
    elif record_type == "milestone":
        records = milestones_visible_to(actor, include_archived=True).filter(
            is_archived=True
        )
    else:
        records = enrollments_visible_to(actor, include_archived=True).filter(
            is_archived=True
        )
        if query:
            records = records.filter(
                Q(trainee__full_name__icontains=query)
                | Q(trainee_number__icontains=query)
                | Q(course__code__icontains=query)
            )
        return cast(
            QuerySet[models.Model],
            records.order_by("-archived_at", "-pk"),
        )
    if normalized:
        records = records.filter(search_key__contains=normalized)
    return cast(QuerySet[models.Model], records.order_by("-archived_at", "-pk"))


def archive_entry(
    record_type: str,
    record: models.Model,
    language_code: str,
) -> ArchiveEntry:
    definition = ARCHIVE_TYPE_BY_CODE[record_type]
    dynamic_record = cast(Any, record)
    record_id = int(record.pk)
    code = _record_code(record_type, record)
    label = _record_label(record_type, record, language_code)
    return ArchiveEntry(
        type_code=record_type,
        type_label=definition.label,
        code=code,
        label=label,
        archived_at=dynamic_record.archived_at,
        restore_url=_restore_url(record_type, record_id),
    )


def latest_recorded_status(kind: str) -> RecordedStatus:
    action = (
        actions.BACKUP_STATUS_RECORDED
        if kind == "backup"
        else actions.RESTORE_TEST_STATUS_RECORDED
    )
    event = AuditEvent.objects.filter(
        scope=AuditEvent.Scope.OPERATIONS,
        action=action,
    ).first()
    if event is None:
        return RecordedStatus("not_recorded")
    completed_at_value = event.metadata.get("completed_at")
    completed_at = (
        parse_datetime(completed_at_value)
        if isinstance(completed_at_value, str)
        else None
    )
    if completed_at is None:
        return RecordedStatus("invalid")
    if timezone.is_naive(completed_at):
        completed_at = timezone.make_aware(completed_at)
    result = str(event.metadata.get("status", ""))
    environment = str(event.metadata.get("environment", ""))
    if result != "succeeded":
        return RecordedStatus("failed", completed_at, environment, result)
    age_limit = RPO_HOURS if kind == "backup" else RESTORE_TEST_INTERVAL_DAYS * 24
    state = (
        "current"
        if timezone.now() - completed_at <= timedelta(hours=age_limit)
        else "stale"
    )
    return RecordedStatus(state, completed_at, environment, result)


def _record_code(record_type: str, record: models.Model) -> str:
    if record_type == "enrollment":
        enrollment = cast(CourseEnrollment, record)
        return f"{enrollment.course.code}:{enrollment.trainee_number}"
    dynamic_record = cast(Any, record)
    return str(dynamic_record.code)


def _record_label(
    record_type: str,
    record: models.Model,
    language_code: str,
) -> str:
    if record_type == "enrollment":
        enrollment = cast(CourseEnrollment, record)
        return enrollment.trainee.full_name
    name_field = "name_ar" if language_code == "ar" else "name_en"
    return str(getattr(record, name_field))


def _restore_url(record_type: str, record_id: int) -> str:
    route_names = {
        "department": "organizations:restore",
        "client": "projects:client_restore",
        "category": "projects:category_restore",
        "project": "projects:restore",
        "trainer": "courses:trainer_restore",
        "course": "courses:restore",
        "tag": "tasks:tag_restore",
        "task": "tasks:restore",
        "milestone": "approvals:milestone_restore",
        "enrollment": "trainees:restore",
    }
    parameter_names = {
        "department": "department_id",
        "client": "record_id",
        "category": "record_id",
        "project": "project_id",
        "trainer": "trainer_id",
        "course": "course_id",
        "tag": "tag_id",
        "task": "task_id",
        "milestone": "milestone_id",
        "enrollment": "enrollment_id",
    }
    return reverse(
        route_names[record_type],
        kwargs={parameter_names[record_type]: record_id},
    )
