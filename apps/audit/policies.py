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
        AuditEvent.Scope.AI_BRIEFINGS,
        AuditEvent.Scope.EXECUTIVE_BOT,
        AuditEvent.Scope.PROJECT_AGENTS,
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
    AuditEvent.Scope.AI_BRIEFINGS: ("ai_briefing",),
    AuditEvent.Scope.EXECUTIVE_BOT: (
        "executive_report",
        "critical_task_alert",
    ),
    AuditEvent.Scope.PROJECT_AGENTS: ("agent_run",),
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
        "alerts",
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
        "evidence_count",
        "evidence_truncated",
        "evidence_window_days",
        "detail_level",
        "failure_code",
        "expires_at",
        "file_id",
        "filters",
        "kind",
        "language",
        "model_code",
        "occurrences",
        "operation_key",
        "policy",
        "project_id",
        "report_type",
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
        "source_count",
        "source_truncated",
        "submission_id",
        "target_id",
        "target_type",
        "window_days",
        "proposal_id",
        "action_code",
        "executed",
    }
)
