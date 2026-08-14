"""Protected Phase 17 agent runs, steps, proposals, and reviewed memory."""

from typing import Any, ClassVar
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProtectedAgentQuerySet[ModelT: models.Model](models.QuerySet[ModelT]):
    def delete(self) -> tuple[int, dict[str, int]]:
        raise PermissionDenied("Project-agent records cannot be hard-deleted.")


class ProtectedAgentModel(models.Model):
    objects = ProtectedAgentQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise PermissionDenied("Project-agent records cannot be hard-deleted.")


class AgentRun(ProtectedAgentModel):
    """One bounded goal-driven project-agent lifecycle."""

    class Goal(models.TextChoices):
        PROJECT_RECOVERY = "project_recovery", _("Project recovery plan")

    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued")
        PLANNING = "planning", _("Planning")
        RUNNING = "running", _("Running")
        AWAITING_APPROVAL = "awaiting_approval", _("Awaiting approval")
        EXECUTING = "executing", _("Executing")
        VERIFYING = "verifying", _("Verifying")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")
        STALE = "stale", _("Stale")

    class Language(models.TextChoices):
        ARABIC = "ar", _("Arabic")
        ENGLISH = "en", _("English")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="agent_runs",
        verbose_name=_("project"),
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_agent_runs",
        verbose_name=_("requester"),
    )
    goal_code = models.CharField(max_length=32, choices=Goal.choices)
    optional_context = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=2, choices=Language.choices)
    provider_code = models.CharField(max_length=24, blank=True)
    model_code = models.CharField(max_length=80)
    prompt_version = models.CharField(max_length=32, default="phase17-v1")
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    current_step = models.PositiveSmallIntegerField(default=0)
    max_steps = models.PositiveSmallIntegerField(default=8)
    max_total_tokens = models.PositiveIntegerField(default=16_000)
    input_tokens = models.PositiveIntegerField(default=0)
    cached_input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    input_fingerprint = models.CharField(max_length=64, db_index=True)
    output_data = models.JSONField(default=dict, blank=True)
    verification_data = models.JSONField(default=dict, blank=True)
    safe_failure_code = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_agent_runs",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        permissions = (
            ("start_agentrun", "Can start project agent runs"),
            ("review_agentrun", "Can review completed project agent runs"),
            ("approve_agentproposal", "Can approve project agent proposals"),
            ("execute_agentproposal", "Can execute approved agent proposals"),
        )
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(goal_code="project_recovery"),
                name="project_agents_goal_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=("ar", "en")),
                name="project_agents_language_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "queued",
                        "planning",
                        "running",
                        "awaiting_approval",
                        "executing",
                        "verifying",
                        "completed",
                        "failed",
                        "cancelled",
                        "expired",
                        "stale",
                    )
                ),
                name="project_agents_run_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    model_code__in=(
                        "openai/gpt-oss-20b",
                        "openai/gpt-oss-120b",
                        "qwen/qwen3.5-9b",
                    )
                ),
                name="project_agents_model_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(max_steps__gte=1) & models.Q(max_steps__lte=8),
                name="project_agents_steps_bounded",
            ),
            models.CheckConstraint(
                condition=models.Q(current_step__lte=models.F("max_steps")),
                name="project_agents_current_step_bounded",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(reviewed_at__isnull=True, reviewed_by__isnull=True)
                    | models.Q(reviewed_at__isnull=False, reviewed_by__isnull=False)
                ),
                name="project_agents_review_state_valid",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("project", "-created_at"), name="agent_run_project_created_idx"
            ),
            models.Index(
                fields=("requester", "-created_at"), name="agent_run_user_created_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.code}:{self.id}:{self.status}"


class AgentStep(ProtectedAgentModel):
    class StepType(models.TextChoices):
        PLAN = "plan", _("Plan")
        TOOL = "tool", _("Tool")
        OBSERVATION = "observation", _("Observation")
        PROPOSAL = "proposal", _("Proposal")
        FINAL = "final", _("Final")
        VERIFICATION = "verification", _("Verification")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    run = models.ForeignKey(AgentRun, on_delete=models.PROTECT, related_name="steps")
    sequence = models.PositiveSmallIntegerField()
    step_type = models.CharField(max_length=16, choices=StepType.choices)
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("sequence",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("run", "sequence"), name="project_agents_step_sequence_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(sequence__gte=1) & models.Q(sequence__lte=8),
                name="project_agents_step_sequence_bounded",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    step_type__in=(
                        "plan",
                        "tool",
                        "observation",
                        "proposal",
                        "final",
                        "verification",
                    )
                ),
                name="project_agents_step_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "pending",
                        "running",
                        "completed",
                        "failed",
                        "cancelled",
                    )
                ),
                name="project_agents_step_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.run_id}:{self.sequence}:{self.step_type}"


class AgentToolCall(ProtectedAgentModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    run = models.ForeignKey(
        AgentRun, on_delete=models.PROTECT, related_name="tool_calls"
    )
    step = models.OneToOneField(
        AgentStep, on_delete=models.PROTECT, related_name="tool_call"
    )
    tool_code = models.CharField(max_length=48)
    arguments = models.JSONField(default=dict)
    safe_result = models.JSONField(default=dict)
    idempotency_key = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    safe_failure_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("step__sequence",)
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    tool_code__in=(
                        "get_project_snapshot",
                        "list_overdue_and_blocked_tasks",
                        "get_upcoming_milestones",
                        "get_pending_approvals",
                        "get_team_workload",
                        "calculate_project_progress",
                        "recall_reviewed_agent_runs",
                    )
                ),
                name="project_agents_tool_code_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("pending", "running", "completed", "failed")
                ),
                name="project_agents_tool_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.run_id}:{self.tool_code}:{self.status}"


class AgentProposal(ProtectedAgentModel):
    class Action(models.TextChoices):
        TASK_UPDATE = "propose_task_update", _("Task update")
        TASK_ASSIGNMENT = "propose_task_assignment", _("Task assignment")
        TASK_COMMENT = "propose_task_comment", _("Task comment")
        DEADLINE_CHANGE = "propose_deadline_change", _("Deadline change")
        TEAM_NOTIFICATION = "propose_team_notification", _("Team notification")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        EXECUTING = "executing", _("Executing")
        EXECUTED = "executed", _("Executed")
        STALE = "stale", _("Stale")
        EXPIRED = "expired", _("Expired")
        FAILED = "failed", _("Failed")

    class Risk(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    run = models.ForeignKey(
        AgentRun, on_delete=models.PROTECT, related_name="proposals"
    )
    step = models.OneToOneField(
        AgentStep, on_delete=models.PROTECT, related_name="proposal"
    )
    action_code = models.CharField(max_length=48, choices=Action.choices)
    payload = models.JSONField(default=dict)
    citations = models.JSONField(default=list)
    before_state = models.JSONField(default=dict)
    before_state_fingerprint = models.CharField(max_length=64)
    risk = models.CharField(max_length=12, choices=Risk.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decided_agent_proposals",
        blank=True,
        null=True,
    )
    decision_reason = models.CharField(max_length=500, blank=True)
    decided_at = models.DateTimeField(blank=True, null=True)
    execution_idempotency_key = models.CharField(max_length=64, unique=True)
    execution_result = models.JSONField(default=dict, blank=True)
    safe_failure_code = models.CharField(max_length=64, blank=True)
    executed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    action_code__in=(
                        "propose_task_update",
                        "propose_task_assignment",
                        "propose_task_comment",
                        "propose_deadline_change",
                        "propose_team_notification",
                    )
                ),
                name="project_agents_proposal_action_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(risk__in=("low", "medium", "high")),
                name="project_agents_proposal_risk_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=("pending", "expired"),
                        approver__isnull=True,
                        decided_at__isnull=True,
                        decision_reason="",
                    )
                    | models.Q(
                        status__in=(
                            "approved",
                            "rejected",
                            "executing",
                            "executed",
                            "stale",
                            "failed",
                        ),
                        approver__isnull=False,
                        decided_at__isnull=False,
                    )
                ),
                name="project_agents_proposal_decision_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.run_id}:{self.action_code}:{self.status}"


class AgentMemory(ProtectedAgentModel):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.PROTECT, related_name="agent_memories"
    )
    source_run = models.OneToOneField(
        AgentRun, on_delete=models.PROTECT, related_name="memory"
    )
    reviewed_summary = models.JSONField(default=dict)
    citations = models.JSONField(default=list)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_agent_memories",
    )
    reviewed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-reviewed_at", "-pk")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("project", "-reviewed_at"), name="agent_memory_proj_rev_idx"
            )
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.source_run_id}"


class AgentReviewedEvent(ProtectedAgentModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        LEASED = "leased", _("Leased")
        ACKNOWLEDGED = "acknowledged", _("Acknowledged")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    memory = models.OneToOneField(
        AgentMemory, on_delete=models.PROTECT, related_name="reviewed_event"
    )
    safe_payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    lease_token_hash = models.CharField(max_length=64, blank=True)
    leased_until = models.DateTimeField(blank=True, null=True)
    callback_code = models.CharField(max_length=32, blank=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="pending",
                        lease_token_hash="",
                        leased_until__isnull=True,
                        callback_code="",
                        acknowledged_at__isnull=True,
                    )
                    | models.Q(
                        status="leased",
                        leased_until__isnull=False,
                        callback_code="",
                        acknowledged_at__isnull=True,
                    )
                    & ~models.Q(lease_token_hash="")
                    | models.Q(
                        status="acknowledged",
                        lease_token_hash="",
                        leased_until__isnull=True,
                        callback_code__in=("notified", "archived", "rejected"),
                        acknowledged_at__isnull=False,
                    )
                    | models.Q(
                        status="failed",
                        lease_token_hash="",
                        leased_until__isnull=True,
                        callback_code="failed",
                        acknowledged_at__isnull=False,
                    )
                ),
                name="project_agents_event_lifecycle_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.memory_id}:{self.status}"


class AgentIntegrationNonce(models.Model):
    """Temporary hash-only replay state; expired rows may be removed."""

    nonce_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("expires_at",)

    def __str__(self) -> str:
        return self.nonce_hash
