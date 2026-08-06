"""Stable audit action codes independent of display language."""

LOGIN_SUCCEEDED = "authentication.login_succeeded"
LOGIN_FAILED = "authentication.login_failed"
LOGIN_LOCKED = "authentication.login_locked"
LOGOUT = "authentication.logout"
PASSWORD_CHANGED = "account.password_changed"
PASSWORD_RESET = "account.password_reset"
ACCOUNT_CREATED = "account.created"
ACCOUNT_UPDATED = "account.updated"
ACCOUNT_DEACTIVATED = "account.deactivated"
ACCOUNT_REACTIVATED = "account.reactivated"
LANGUAGE_CHANGED = "account.language_changed"
DEPARTMENT_CREATED = "department.created"
DEPARTMENT_UPDATED = "department.updated"
DEPARTMENT_ARCHIVED = "department.archived"
DEPARTMENT_RESTORED = "department.restored"
PROJECT_CREATED = "project.created"
PROJECT_UPDATED = "project.updated"
PROJECT_STATUS_CHANGED = "project.status_changed"
PROJECT_ARCHIVED = "project.archived"
PROJECT_RESTORED = "project.restored"
PROJECT_TEAM_UPDATED = "project.team_updated"
CLIENT_CREATED = "client.created"
CLIENT_UPDATED = "client.updated"
CLIENT_ARCHIVED = "client.archived"
CLIENT_RESTORED = "client.restored"
CATEGORY_CREATED = "category.created"
CATEGORY_UPDATED = "category.updated"
CATEGORY_ARCHIVED = "category.archived"
CATEGORY_RESTORED = "category.restored"
COURSE_CREATED = "course.created"
COURSE_UPDATED = "course.updated"
COURSE_STATUS_CHANGED = "course.status_changed"
COURSE_ARCHIVED = "course.archived"
COURSE_RESTORED = "course.restored"
COURSE_TRAINERS_UPDATED = "course.trainers_updated"
COURSE_FILE_UPLOADED = "course.file_uploaded"
TRAINER_CREATED = "trainer.created"
TRAINER_UPDATED = "trainer.updated"
TRAINER_ARCHIVED = "trainer.archived"
TRAINER_RESTORED = "trainer.restored"
TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
TASK_STATUS_CHANGED = "task.status_changed"
TASK_ARCHIVED = "task.archived"
TASK_RESTORED = "task.restored"
TASK_ASSIGNMENTS_UPDATED = "task.assignments_updated"
TASK_TAGS_UPDATED = "task.tags_updated"
TASK_COMMENT_ADDED = "task.comment_added"
TASK_FILE_UPLOADED = "task.file_uploaded"
TAG_CREATED = "tag.created"
TAG_UPDATED = "tag.updated"
TAG_ARCHIVED = "tag.archived"
TAG_RESTORED = "tag.restored"
MILESTONE_CREATED = "milestone.created"
MILESTONE_UPDATED = "milestone.updated"
MILESTONE_ARCHIVED = "milestone.archived"
MILESTONE_RESTORED = "milestone.restored"
APPROVAL_SUBMITTED = "approval.submitted"
APPROVAL_APPROVED = "approval.approved"
APPROVAL_REJECTED = "approval.rejected"
TRAINEE_ENROLLED = "trainee.enrolled"
TRAINEE_UPDATED = "trainee.updated"
TRAINEE_ARCHIVED = "trainee.archived"
TRAINEE_RESTORED = "trainee.restored"
TRAINEE_IMPORT_PREVIEWED = "trainee.import_previewed"
TRAINEE_IMPORT_CONFIRMED = "trainee.import_confirmed"
TRAINEE_IMPORT_CANCELLED = "trainee.import_cancelled"
SESSION_CREATED = "session.created"
SESSION_ARCHIVED = "session.archived"
TRAINER_LINK_ISSUED = "trainer_link.issued"
ATTENDANCE_SUBMITTED = "attendance.submitted"
ATTENDANCE_RESUBMITTED = "attendance.resubmitted"
ATTENDANCE_APPROVED = "attendance.approved"
ATTENDANCE_REJECTED = "attendance.rejected"
ATTENDANCE_CORRECTED = "attendance.corrected"
NOTIFICATION_PREFERENCES_UPDATED = "notification.preferences_updated"
AUDIT_EXPORTED = "audit.exported"
BACKUP_STATUS_RECORDED = "backup.status_recorded"
RESTORE_TEST_STATUS_RECORDED = "backup.restore_test_status_recorded"
RETENTION_INVENTORY_RECORDED = "retention.inventory_recorded"
AI_BRIEFING_REQUESTED = "ai_briefing.requested"
AI_BRIEFING_COMPLETED = "ai_briefing.completed"
AI_BRIEFING_FAILED = "ai_briefing.failed"
AI_BRIEFING_REVIEWED = "ai_briefing.reviewed"
EXECUTIVE_REPORT_REQUESTED = "executive_report.requested"
EXECUTIVE_REPORT_COMPLETED = "executive_report.completed"
EXECUTIVE_REPORT_FAILED = "executive_report.failed"
EXECUTIVE_REPORT_DOWNLOADED = "executive_report.downloaded"
CRITICAL_ALERT_DELIVERED = "critical_alert.delivered"
EXECUTIVE_ASSISTANT_REQUESTED = "executive_assistant.requested"
EXECUTIVE_ASSISTANT_COMPLETED = "executive_assistant.completed"
EXECUTIVE_ASSISTANT_FAILED = "executive_assistant.failed"
AGENT_RUN_REQUESTED = "project_agent.run_requested"
AGENT_RUN_AWAITING_APPROVAL = "project_agent.awaiting_approval"
AGENT_RUN_COMPLETED = "project_agent.run_completed"
AGENT_RUN_FAILED = "project_agent.run_failed"
AGENT_RUN_CANCELLED = "project_agent.run_cancelled"
AGENT_RUN_REVIEWED = "project_agent.run_reviewed"
AGENT_TOOL_COMPLETED = "project_agent.tool_completed"
AGENT_TOOL_FAILED = "project_agent.tool_failed"
AGENT_PROPOSAL_CREATED = "project_agent.proposal_created"
AGENT_PROPOSAL_APPROVED = "project_agent.proposal_approved"
AGENT_PROPOSAL_REJECTED = "project_agent.proposal_rejected"
AGENT_PROPOSAL_EXECUTED = "project_agent.proposal_executed"
AGENT_PROPOSAL_STALE = "project_agent.proposal_stale"
AGENT_PROPOSAL_FAILED = "project_agent.proposal_failed"
AGENT_PROPOSAL_EXPIRED = "project_agent.proposal_expired"

ALL_ACTION_CODES = (
    LOGIN_SUCCEEDED,
    LOGIN_FAILED,
    LOGIN_LOCKED,
    LOGOUT,
    PASSWORD_CHANGED,
    PASSWORD_RESET,
    ACCOUNT_CREATED,
    ACCOUNT_UPDATED,
    ACCOUNT_DEACTIVATED,
    ACCOUNT_REACTIVATED,
    LANGUAGE_CHANGED,
    DEPARTMENT_CREATED,
    DEPARTMENT_UPDATED,
    DEPARTMENT_ARCHIVED,
    DEPARTMENT_RESTORED,
    PROJECT_CREATED,
    PROJECT_UPDATED,
    PROJECT_STATUS_CHANGED,
    PROJECT_ARCHIVED,
    PROJECT_RESTORED,
    PROJECT_TEAM_UPDATED,
    CLIENT_CREATED,
    CLIENT_UPDATED,
    CLIENT_ARCHIVED,
    CLIENT_RESTORED,
    CATEGORY_CREATED,
    CATEGORY_UPDATED,
    CATEGORY_ARCHIVED,
    CATEGORY_RESTORED,
    COURSE_CREATED,
    COURSE_UPDATED,
    COURSE_STATUS_CHANGED,
    COURSE_ARCHIVED,
    COURSE_RESTORED,
    COURSE_TRAINERS_UPDATED,
    COURSE_FILE_UPLOADED,
    TRAINER_CREATED,
    TRAINER_UPDATED,
    TRAINER_ARCHIVED,
    TRAINER_RESTORED,
    TASK_CREATED,
    TASK_UPDATED,
    TASK_STATUS_CHANGED,
    TASK_ARCHIVED,
    TASK_RESTORED,
    TASK_ASSIGNMENTS_UPDATED,
    TASK_TAGS_UPDATED,
    TASK_COMMENT_ADDED,
    TASK_FILE_UPLOADED,
    TAG_CREATED,
    TAG_UPDATED,
    TAG_ARCHIVED,
    TAG_RESTORED,
    MILESTONE_CREATED,
    MILESTONE_UPDATED,
    MILESTONE_ARCHIVED,
    MILESTONE_RESTORED,
    APPROVAL_SUBMITTED,
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
    TRAINEE_ENROLLED,
    TRAINEE_UPDATED,
    TRAINEE_ARCHIVED,
    TRAINEE_RESTORED,
    TRAINEE_IMPORT_PREVIEWED,
    TRAINEE_IMPORT_CONFIRMED,
    TRAINEE_IMPORT_CANCELLED,
    SESSION_CREATED,
    SESSION_ARCHIVED,
    TRAINER_LINK_ISSUED,
    ATTENDANCE_SUBMITTED,
    ATTENDANCE_RESUBMITTED,
    ATTENDANCE_APPROVED,
    ATTENDANCE_REJECTED,
    ATTENDANCE_CORRECTED,
    NOTIFICATION_PREFERENCES_UPDATED,
    AUDIT_EXPORTED,
    BACKUP_STATUS_RECORDED,
    RESTORE_TEST_STATUS_RECORDED,
    RETENTION_INVENTORY_RECORDED,
    AI_BRIEFING_REQUESTED,
    AI_BRIEFING_COMPLETED,
    AI_BRIEFING_FAILED,
    AI_BRIEFING_REVIEWED,
    EXECUTIVE_REPORT_REQUESTED,
    EXECUTIVE_REPORT_COMPLETED,
    EXECUTIVE_REPORT_FAILED,
    EXECUTIVE_REPORT_DOWNLOADED,
    CRITICAL_ALERT_DELIVERED,
    EXECUTIVE_ASSISTANT_REQUESTED,
    EXECUTIVE_ASSISTANT_COMPLETED,
    EXECUTIVE_ASSISTANT_FAILED,
    AGENT_RUN_REQUESTED,
    AGENT_RUN_AWAITING_APPROVAL,
    AGENT_RUN_COMPLETED,
    AGENT_RUN_FAILED,
    AGENT_RUN_CANCELLED,
    AGENT_RUN_REVIEWED,
    AGENT_TOOL_COMPLETED,
    AGENT_TOOL_FAILED,
    AGENT_PROPOSAL_CREATED,
    AGENT_PROPOSAL_APPROVED,
    AGENT_PROPOSAL_REJECTED,
    AGENT_PROPOSAL_EXECUTED,
    AGENT_PROPOSAL_STALE,
    AGENT_PROPOSAL_FAILED,
    AGENT_PROPOSAL_EXPIRED,
)
