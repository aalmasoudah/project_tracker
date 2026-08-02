"""Safe operational status and command-facing record services."""

import hashlib
from dataclasses import dataclass
from datetime import datetime

from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections, transaction

from apps.accounts.models import User
from apps.approvals.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStep,
    Milestone,
)
from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceEntry,
    AttendanceEvidence,
    AttendanceReview,
    AttendanceSubmission,
    Session,
    SessionParticipant,
    TrainerLink,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.courses.models import Course, CourseFile, CourseTrainerAssignment, Trainer
from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    NotificationPreference,
)
from apps.operations.policies import RETENTION_POLICY_CODE
from apps.organizations.models import Department
from apps.projects.models import Category, Client, Project, ProjectMembership
from apps.tasks.models import (
    Tag,
    Task,
    TaskAssignment,
    TaskComment,
    TaskFile,
    TaskTag,
)
from apps.trainees.models import CourseEnrollment, ImportBatch, ImportRow, Trainee


@dataclass(frozen=True)
class RetentionInventory:
    counts: dict[str, int]
    deletion_candidates: int = 0
    policy: str = RETENTION_POLICY_CODE

    @property
    def total_records(self) -> int:
        return sum(self.counts.values())


PROTECTED_MODELS = (
    User,
    Department,
    AuditEvent,
    Client,
    Category,
    Project,
    ProjectMembership,
    Trainer,
    Course,
    CourseTrainerAssignment,
    CourseFile,
    Task,
    TaskAssignment,
    Tag,
    TaskTag,
    TaskComment,
    TaskFile,
    Milestone,
    ApprovalRequest,
    ApprovalStep,
    ApprovalDecision,
    Trainee,
    CourseEnrollment,
    ImportBatch,
    ImportRow,
    Session,
    SessionParticipant,
    TrainerLink,
    AttendanceSubmission,
    AttendanceEntry,
    AttendanceEvidence,
    AttendanceReview,
    AttendanceCorrection,
    Notification,
    NotificationPreference,
    DeliveryAttempt,
)


def database_status() -> str:
    connection = connections[DEFAULT_DB_ALIAS].copy(alias="operations_health")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return "unavailable"
    finally:
        connection.close()
    return "ok"


def retention_inventory() -> RetentionInventory:
    counts = {
        f"{model._meta.app_label}.{model._meta.model_name}": model.objects.count()
        for model in PROTECTED_MODELS
    }
    return RetentionInventory(counts=counts)


@transaction.atomic
def record_backup_verification(
    *,
    kind: str,
    environment: str,
    status: str,
    completed_at: datetime,
) -> tuple[AuditEvent, bool]:
    operation_source = (
        f"{kind}|{environment}|{status}|{completed_at.isoformat(timespec='seconds')}"
    )
    operation_key = hashlib.sha256(operation_source.encode()).hexdigest()
    existing = AuditEvent.objects.filter(
        scope=AuditEvent.Scope.OPERATIONS,
        metadata__operation_key=operation_key,
    ).first()
    if existing is not None:
        return existing, False
    action = (
        actions.BACKUP_STATUS_RECORDED
        if kind == "backup"
        else actions.RESTORE_TEST_STATUS_RECORDED
    )
    event = record_audit_event(
        action=action,
        target_type=kind,
        target_label=environment,
        metadata={
            "completed_at": completed_at.isoformat(),
            "environment": environment,
            "kind": kind,
            "operation_key": operation_key,
            "status": status,
        },
        scope=AuditEvent.Scope.OPERATIONS,
    )
    return event, True


@transaction.atomic
def record_retention_inventory(
    *,
    environment: str,
    inventory: RetentionInventory,
    operation_key: str,
) -> tuple[AuditEvent, bool]:
    existing = AuditEvent.objects.filter(
        scope=AuditEvent.Scope.OPERATIONS,
        metadata__operation_key=operation_key,
    ).first()
    if existing is not None:
        return existing, False
    event = record_audit_event(
        action=actions.RETENTION_INVENTORY_RECORDED,
        target_type="retention_inventory",
        target_label=environment,
        metadata={
            "deletion_candidates": inventory.deletion_candidates,
            "environment": environment,
            "operation_key": operation_key,
            "policy": inventory.policy,
        },
        scope=AuditEvent.Scope.OPERATIONS,
    )
    return event, True
