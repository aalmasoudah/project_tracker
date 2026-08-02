"""Approved Phase 14 audit boundaries."""

from typing import Final

from apps.audit.models import AuditEvent

MAX_AUDIT_RANGE_DAYS: Final = 366
MAX_AUDIT_EXPORT_ROWS: Final = 5_000

SECURITY_AUDIT_SCOPES: Final = frozenset(
    {AuditEvent.Scope.SECURITY, AuditEvent.Scope.OPERATIONS}
)
BUSINESS_AUDIT_SCOPES: Final = frozenset(
    {
        AuditEvent.Scope.PROJECTS,
        AuditEvent.Scope.COURSES,
        AuditEvent.Scope.TASKS,
        AuditEvent.Scope.APPROVALS,
        AuditEvent.Scope.TRAINEES,
        AuditEvent.Scope.ATTENDANCE,
        AuditEvent.Scope.NOTIFICATIONS,
    }
)

TARGET_TYPES_BY_SCOPE: Final[dict[str, tuple[str, ...]]] = {
    AuditEvent.Scope.SECURITY: ("authentication", "account", "department"),
    AuditEvent.Scope.PROJECTS: ("project", "client", "category"),
    AuditEvent.Scope.COURSES: ("course", "trainer"),
    AuditEvent.Scope.TASKS: ("task", "tag"),
    AuditEvent.Scope.APPROVALS: (
        "approval_request",
        "course",
        "milestone",
        "project",
        "task",
    ),
    AuditEvent.Scope.TRAINEES: ("enrollment", "import_batch"),
    AuditEvent.Scope.ATTENDANCE: ("session",),
    AuditEvent.Scope.NOTIFICATIONS: ("notification_preferences",),
    AuditEvent.Scope.OPERATIONS: (
        "audit_export",
        "backup",
        "restore_test",
        "retention_inventory",
    ),
}

SAFE_METADATA_KEYS: Final = frozenset(
    {
        "added_trainer_ids",
        "added_user_ids",
        "attempt",
        "backup_status",
        "categories",
        "changed_fields",
        "completed_at",
        "correction_id",
        "deletion_candidates",
        "entries",
        "environment",
        "errors",
        "evidence",
        "expires_at",
        "file_id",
        "filters",
        "kind",
        "language",
        "occurrences",
        "operation_key",
        "policy",
        "previous_status",
        "recurrence",
        "removed_trainer_ids",
        "removed_user_ids",
        "restore_test_status",
        "review_attempt",
        "revoked_other_sessions",
        "revoked_sessions",
        "role",
        "rows",
        "sequence",
        "size",
        "status",
        "submission_id",
        "target_id",
        "target_type",
    }
)
