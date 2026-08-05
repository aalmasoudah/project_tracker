"""Bounded Phase 17 agent lifecycle and controlled domain execution."""

import hashlib
import json
import time
from datetime import datetime, timedelta
from datetime import time as datetime_time
from decimal import Decimal
from functools import partial
from typing import cast
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.notifications.services import create_notification
from apps.project_agents.models import (
    AgentMemory,
    AgentProposal,
    AgentReviewedEvent,
    AgentRun,
    AgentStep,
    AgentToolCall,
)
from apps.project_agents.policies import (
    can_decide_agent_proposal,
    can_execute_agent_proposal,
    can_review_agent_run,
    can_start_agent,
)
from apps.project_agents.providers import get_agent_provider
from apps.project_agents.providers.base import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderResult,
    TemporaryProviderError,
)
from apps.project_agents.schemas import (
    AgentDecision,
    AgentSchemaError,
    validate_decision,
    validate_proposal_payload,
)
from apps.project_agents.tools import (
    execute_read_tool,
    observed_references,
)
from apps.projects.models import Project
from apps.projects.selectors import can_manage_project
from apps.tasks.models import Task
from apps.tasks.selectors import (
    can_manage_task,
    can_update_assigned_task,
    tasks_visible_to,
)
from apps.tasks.services import (
    add_task_comment,
    replace_task_assignments,
    update_assigned_task,
    update_task,
)

TERMINAL_RUN_STATUSES = frozenset(
    {
        AgentRun.Status.COMPLETED,
        AgentRun.Status.FAILED,
        AgentRun.Status.CANCELLED,
        AgentRun.Status.EXPIRED,
        AgentRun.Status.STALE,
    }
)
APPROVED_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})
ACTION_RISKS: dict[str, str] = {
    AgentProposal.Action.TASK_COMMENT: AgentProposal.Risk.LOW,
    AgentProposal.Action.TEAM_NOTIFICATION: AgentProposal.Risk.LOW,
    AgentProposal.Action.TASK_UPDATE: AgentProposal.Risk.MEDIUM,
    AgentProposal.Action.TASK_ASSIGNMENT: AgentProposal.Risk.MEDIUM,
    AgentProposal.Action.DEADLINE_CHANGE: AgentProposal.Risk.HIGH,
}


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _audit(
    *,
    actor: User | None,
    action: str,
    run: AgentRun,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="agent_run",
        target_id=str(run.pk),
        target_label=run.project.code,
        metadata=metadata or {},
        request=request,
        scope=AuditEvent.Scope.PROJECT_AGENTS,
    )


def _enqueue_run(run_id: object) -> None:
    from apps.project_agents.tasks import process_project_agent

    process_project_agent.delay(str(run_id))


def _enqueue_proposal(proposal_id: object) -> None:
    from apps.project_agents.tasks import execute_project_agent_proposal

    execute_project_agent_proposal.delay(str(proposal_id))


@transaction.atomic
def request_agent_run(
    *,
    actor: User,
    project: Project,
    goal_code: str,
    optional_context: str,
    language: str,
    model_code: str,
    request: HttpRequest | None = None,
) -> AgentRun:
    project = Project.objects.select_for_update().get(pk=project.pk)
    if not can_start_agent(actor, project):
        raise PermissionDenied(_("Project-agent permission is required."))
    if goal_code not in AgentRun.Goal.values:
        raise ValidationError(_("Select a valid project-agent goal."))
    if language not in AgentRun.Language.values:
        raise ValidationError(_("Select a valid language."))
    if model_code not in APPROVED_MODELS:
        raise ValidationError(_("Select an approved project-agent model."))
    optional_context = " ".join(optional_context.split())
    if len(optional_context) > int(settings.PROJECT_AGENT_MAX_CONTEXT_CHARS):
        raise ValidationError(_("Optional context is too long."))
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today, datetime_time.min))
    # Serialize requests per actor so concurrent requests cannot bypass the
    # configured daily quota.
    User.objects.select_for_update().only("pk").get(pk=actor.pk)
    if AgentRun.objects.filter(requester=actor, created_at__gte=start).count() >= int(
        settings.PROJECT_AGENT_DAILY_LIMIT
    ):
        raise ValidationError(_("The daily project-agent request limit was reached."))
    inputs = {
        "project_id": project.pk,
        "requester_id": actor.pk,
        "goal_code": goal_code,
        "optional_context": optional_context,
        "language": language,
        "model_code": model_code,
    }
    run = AgentRun.objects.create(
        project=project,
        requester=actor,
        goal_code=goal_code,
        optional_context=optional_context,
        language=language,
        model_code=model_code,
        max_steps=int(settings.PROJECT_AGENT_MAX_STEPS),
        max_total_tokens=int(settings.PROJECT_AGENT_MAX_TOTAL_TOKENS),
        input_fingerprint=_fingerprint(inputs),
    )
    _audit(actor=actor, action=actions.AGENT_RUN_REQUESTED, run=run, request=request)
    transaction.on_commit(partial(_enqueue_run, run.pk))
    return run


def _step_context(run: AgentRun) -> list[dict[str, object]]:
    context: list[dict[str, object]] = []
    for step in run.steps.filter(status=AgentStep.Status.COMPLETED).order_by(
        "sequence"
    ):
        data = step.data if isinstance(step.data, dict) else {}
        item: dict[str, object] = {"sequence": step.sequence, "type": step.step_type}
        if step.step_type == AgentStep.StepType.PLAN:
            item["summary"] = data.get("summary", "")
            item["plan_steps"] = data.get("plan_steps", [])
        elif step.step_type == AgentStep.StepType.TOOL:
            item["tool_code"] = data.get("tool_code", "")
        elif step.step_type == AgentStep.StepType.OBSERVATION:
            item["tool_code"] = data.get("tool_code", "")
            item["result"] = data.get("result", {})
        elif step.step_type == AgentStep.StepType.PROPOSAL:
            item["action_code"] = data.get("action_code", "")
            item["citations"] = data.get("citations", [])
        elif step.step_type == AgentStep.StepType.FINAL:
            item["summary"] = data.get("summary", "")
        context.append(item)
    return context


def _provider_context(run: AgentRun) -> dict[str, object]:
    citations, _tasks, _users = observed_references(run)
    tools_used = list(
        run.tool_calls.filter(status=AgentToolCall.Status.COMPLETED)
        .order_by("step__sequence")
        .values_list("tool_code", flat=True)
    )
    return {
        "goal_code": run.goal_code,
        "language": run.language,
        "optional_context_untrusted": run.optional_context,
        "project_id": run.project_id,
        "steps": _step_context(run),
        "tools_used": tools_used,
        "observed_refs": sorted(citations),
        "reviewed_memory_available": AgentMemory.objects.filter(
            project_id=run.project_id,
            source_run__status=AgentRun.Status.COMPLETED,
            source_run__reviewed_at__isnull=False,
        )
        .exclude(source_run_id=run.pk)
        .exists(),
        "remaining_steps": run.max_steps - run.current_step,
        "remaining_tokens": run.max_total_tokens - run.input_tokens - run.output_tokens,
    }


def _create_step(
    *,
    run: AgentRun,
    step_type: str,
    data: dict[str, object],
    duration_ms: int | None = None,
) -> AgentStep:
    next_sequence = run.current_step + 1
    if next_sequence > run.max_steps:
        raise AgentSchemaError("The project-agent step limit was reached.")
    step = AgentStep.objects.create(
        run=run,
        sequence=next_sequence,
        step_type=step_type,
        data=data,
        status=AgentStep.Status.COMPLETED,
        duration_ms=duration_ms,
        completed_at=timezone.now(),
    )
    run.current_step = next_sequence
    run.save(update_fields=("current_step", "updated_at"))
    return step


def _apply_usage(run: AgentRun, result: ProviderResult) -> None:
    input_tokens = int(result.input_tokens or 0)
    cached_tokens = int(result.cached_input_tokens or 0)
    output_tokens = int(result.output_tokens or 0)
    if (
        run.input_tokens + run.output_tokens + input_tokens + output_tokens
        > run.max_total_tokens
    ):
        raise AgentSchemaError("The project-agent token budget was exceeded.")
    run.input_tokens += input_tokens
    run.cached_input_tokens += cached_tokens
    run.output_tokens += output_tokens
    run.provider_code = result.provider_code[:24]
    run.save(
        update_fields=(
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "provider_code",
            "updated_at",
        )
    )


def _task_for_proposal(run: AgentRun, task_id: int) -> Task:
    try:
        task = (
            tasks_visible_to(run.requester)
            .select_related("project", "course", "course__project", "parent")
            .get(pk=task_id)
        )
    except Task.DoesNotExist as error:
        raise PermissionDenied(
            "The proposed task is outside the current scope."
        ) from error
    project_id = task.project_id or task.course.project_id  # type: ignore[union-attr]
    if project_id != run.project_id:
        raise PermissionDenied("The proposed task is outside the run project.")
    return task


def _task_state(task: Task) -> dict[str, object]:
    assignments = list(
        task.assignments.filter(removed_at__isnull=True)
        .order_by("user_id")
        .values("user_id", "is_primary")
    )
    return {
        "type": "task",
        "id": task.pk,
        "code": task.code,
        "status": task.status,
        "actual_hours": str(task.actual_hours)
        if task.actual_hours is not None
        else None,
        "blocking_reason": task.blocking_reason,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "assignments": assignments,
        "comment_count": task.comments.count(),
        "updated_at": task.updated_at.isoformat(),
    }


def _project_notification_state(project: Project) -> dict[str, object]:
    member_ids = set(
        project.memberships.filter(
            removed_at__isnull=True, user__is_active=True
        ).values_list("user_id", flat=True)
    )
    member_ids.add(project.manager_id)
    if project.supervisor_id:
        member_ids.add(project.supervisor_id)
    return {
        "type": "project_team",
        "id": project.pk,
        "member_ids": sorted(member_ids),
        "status": project.status,
        "archived": project.is_archived,
        "updated_at": project.updated_at.isoformat(),
    }


def _before_state(
    run: AgentRun, action_code: str, payload: dict[str, object]
) -> dict[str, object]:
    if action_code == AgentProposal.Action.TEAM_NOTIFICATION:
        project = Project.objects.get(pk=run.project_id)
        return _project_notification_state(project)
    task_id = payload.get("task_id")
    if not isinstance(task_id, int):
        raise AgentSchemaError("A task proposal requires a task identifier.")
    return _task_state(_task_for_proposal(run, task_id))


def _create_proposal(
    run: AgentRun, decision: AgentDecision, *, duration_ms: int
) -> AgentProposal:
    _citations, task_ids, user_ids = observed_references(run)
    action_code = cast(str, decision["action_code"])
    payload = validate_proposal_payload(
        action_code,
        decision["payload"],
        observed_task_ids=task_ids,
        observed_user_ids=user_ids,
    )
    before = _before_state(run, action_code, payload)
    step = _create_step(
        run=run,
        step_type=AgentStep.StepType.PROPOSAL,
        data={
            "summary": decision["summary"],
            "action_code": action_code,
            "payload": payload,
            "citations": decision["citations"],
        },
        duration_ms=duration_ms,
    )
    proposal = AgentProposal.objects.create(
        run=run,
        step=step,
        action_code=action_code,
        payload=payload,
        citations=decision["citations"],
        before_state=before,
        before_state_fingerprint=_fingerprint(before),
        risk=ACTION_RISKS[action_code],
        execution_idempotency_key=_fingerprint(
            {"run": str(run.pk), "step": step.sequence, "action": action_code}
        ),
    )
    _audit(
        actor=run.requester,
        action=actions.AGENT_PROPOSAL_CREATED,
        run=run,
        metadata={
            "proposal_id": str(proposal.pk),
            "action_code": proposal.action_code,
        },
    )
    return proposal


def _distinct_tools(run: AgentRun) -> int:
    return (
        run.tool_calls.filter(status=AgentToolCall.Status.COMPLETED)
        .values("tool_code")
        .distinct()
        .count()
    )


def process_agent_run(*, run_id: UUID | str) -> str:
    with transaction.atomic():
        run = (
            AgentRun.objects.select_for_update()
            .select_related("project", "requester")
            .get(pk=run_id)
        )
        if (
            run.status in TERMINAL_RUN_STATUSES
            or run.status == AgentRun.Status.AWAITING_APPROVAL
        ):
            return run.status
        if run.status != AgentRun.Status.QUEUED:
            return run.status
        if not can_start_agent(run.requester, run.project):
            return mark_agent_run_failed(run_id=run.pk, failure_code="access_revoked")
        if run.started_at is None:
            run.started_at = timezone.now()
        run.status = (
            AgentRun.Status.PLANNING
            if run.current_step == 0
            else AgentRun.Status.RUNNING
        )
        run.save(update_fields=("started_at", "status", "updated_at"))
    try:
        provider = get_agent_provider(model_code=run.model_code)
        while run.current_step < run.max_steps:
            run = AgentRun.objects.select_related("project", "requester").get(pk=run.pk)
            if run.status == AgentRun.Status.CANCELLED:
                return run.status
            if run.status not in (
                AgentRun.Status.PLANNING,
                AgentRun.Status.RUNNING,
            ):
                return run.status
            if not can_start_agent(run.requester, run.project):
                return mark_agent_run_failed(
                    run_id=run.pk, failure_code="access_revoked"
                )
            if run.started_at is not None and (
                timezone.now() - run.started_at
            ).total_seconds() > int(settings.PROJECT_AGENT_MAX_SECONDS):
                return mark_agent_run_failed(
                    run_id=run.pk, failure_code="time_budget_exceeded"
                )
            allowed_refs, _task_ids, _user_ids = observed_references(run)
            call_started = time.monotonic()
            provider_result = provider.decide(context=_provider_context(run))
            duration_ms = int((time.monotonic() - call_started) * 1000)
            run = AgentRun.objects.select_related("project", "requester").get(pk=run.pk)
            if run.status == AgentRun.Status.CANCELLED:
                return run.status
            if run.status not in (
                AgentRun.Status.PLANNING,
                AgentRun.Status.RUNNING,
            ):
                return run.status
            if not can_start_agent(run.requester, run.project):
                return mark_agent_run_failed(
                    run_id=run.pk, failure_code="access_revoked"
                )
            if run.started_at is not None and (
                timezone.now() - run.started_at
            ).total_seconds() > int(settings.PROJECT_AGENT_MAX_SECONDS):
                return mark_agent_run_failed(
                    run_id=run.pk, failure_code="time_budget_exceeded"
                )
            _apply_usage(run, provider_result)
            decision = validate_decision(
                provider_result.data, allowed_citations=allowed_refs
            )
            if run.current_step == 0 and decision["kind"] != "plan":
                raise AgentSchemaError("The first agent decision must be a plan.")
            if decision["kind"] == "plan":
                if run.steps.exists():
                    raise AgentSchemaError("An agent run can contain only one plan.")
                _create_step(
                    run=run,
                    step_type=AgentStep.StepType.PLAN,
                    data={
                        "summary": decision["summary"],
                        "plan_steps": decision["plan_steps"],
                    },
                    duration_ms=duration_ms,
                )
                run.status = AgentRun.Status.RUNNING
                run.save(update_fields=("status", "updated_at"))
                continue
            if decision["kind"] == "tool_call":
                if run.current_step + 2 > run.max_steps:
                    raise AgentSchemaError("The project-agent step limit was reached.")
                tool_code = cast(str, decision["tool_code"])
                if run.tool_calls.filter(tool_code=tool_code).exists():
                    raise AgentSchemaError("A read tool cannot be repeated in one run.")
                step = _create_step(
                    run=run,
                    step_type=AgentStep.StepType.TOOL,
                    data={"tool_code": tool_code, "arguments": {}},
                    duration_ms=duration_ms,
                )
                call = AgentToolCall.objects.create(
                    run=run,
                    step=step,
                    tool_code=tool_code,
                    arguments={},
                    idempotency_key=_fingerprint(
                        {"run": str(run.pk), "step": step.sequence, "tool": tool_code}
                    ),
                    status=AgentToolCall.Status.RUNNING,
                )
                tool_started = time.monotonic()
                try:
                    result = execute_read_tool(
                        run=run, actor=run.requester, tool_code=tool_code
                    )
                except (PermissionDenied, ValidationError) as error:
                    call.status = AgentToolCall.Status.FAILED
                    call.safe_failure_code = (
                        "access_revoked"
                        if isinstance(error, PermissionDenied)
                        else "tool_validation_failed"
                    )
                    call.completed_at = timezone.now()
                    call.save(
                        update_fields=(
                            "status",
                            "safe_failure_code",
                            "completed_at",
                        )
                    )
                    step.status = AgentStep.Status.FAILED
                    step.save(update_fields=("status",))
                    _audit(
                        actor=run.requester,
                        action=actions.AGENT_TOOL_FAILED,
                        run=run,
                        metadata={
                            "tool_call_id": call.pk,
                            "tool_code": tool_code,
                            "failure_code": call.safe_failure_code,
                        },
                    )
                    raise
                call.safe_result = result
                call.status = AgentToolCall.Status.COMPLETED
                call.completed_at = timezone.now()
                call.save(update_fields=("safe_result", "status", "completed_at"))
                _audit(
                    actor=run.requester,
                    action=actions.AGENT_TOOL_COMPLETED,
                    run=run,
                    metadata={"tool_call_id": call.pk, "tool_code": tool_code},
                )
                _create_step(
                    run=run,
                    step_type=AgentStep.StepType.OBSERVATION,
                    data={"tool_code": tool_code, "result": result},
                    duration_ms=int((time.monotonic() - tool_started) * 1000),
                )
                continue
            if _distinct_tools(run) < 2:
                raise AgentSchemaError("At least two distinct read tools are required.")
            if decision["kind"] == "proposal":
                if run.proposals.exists():
                    raise AgentSchemaError("The pilot run supports one proposal.")
                _create_proposal(run, decision, duration_ms=duration_ms)
                _create_step(
                    run=run,
                    step_type=AgentStep.StepType.FINAL,
                    data={
                        "summary": decision["summary"],
                        "findings": decision["findings"],
                        "recommendations": decision["recommendations"],
                    },
                )
                run.output_data = {
                    "summary": decision["summary"],
                    "findings": decision["findings"],
                    "recommendations": decision["recommendations"],
                }
                run.status = AgentRun.Status.AWAITING_APPROVAL
                run.save(update_fields=("output_data", "status", "updated_at"))
                _audit(
                    actor=run.requester,
                    action=actions.AGENT_RUN_AWAITING_APPROVAL,
                    run=run,
                )
                return run.status
            if not run.proposals.exists() and run.current_step >= run.max_steps:
                raise AgentSchemaError("Verification capacity is required.")
            _create_step(
                run=run,
                step_type=AgentStep.StepType.FINAL,
                data={
                    "summary": decision["summary"],
                    "findings": decision["findings"],
                    "recommendations": decision["recommendations"],
                },
                duration_ms=duration_ms,
            )
            run.output_data = {
                "summary": decision["summary"],
                "findings": decision["findings"],
                "recommendations": decision["recommendations"],
            }
            if run.proposals.filter(status=AgentProposal.Status.PENDING).exists():
                run.status = AgentRun.Status.AWAITING_APPROVAL
                run.save(update_fields=("output_data", "status", "updated_at"))
                _audit(
                    actor=run.requester,
                    action=actions.AGENT_RUN_AWAITING_APPROVAL,
                    run=run,
                )
                return run.status
            return _complete_without_execution(run)
        raise AgentSchemaError("The project-agent step limit was reached.")
    except TemporaryProviderError:
        _requeue_agent_run_for_retry(run_id=run.pk)
        raise
    except (
        AgentSchemaError,
        ProviderConfigurationError,
        ProviderResponseError,
        PermissionDenied,
        ValidationError,
    ) as error:
        failure = (
            "access_revoked"
            if isinstance(error, PermissionDenied)
            else "invalid_provider_decision"
            if isinstance(error, (AgentSchemaError, ProviderResponseError))
            else "configuration_error"
            if isinstance(error, ProviderConfigurationError)
            else "tool_validation_failed"
        )
        return mark_agent_run_failed(run_id=run.pk, failure_code=failure)


@transaction.atomic
def _requeue_agent_run_for_retry(*, run_id: UUID | str) -> str:
    run = AgentRun.objects.select_for_update().get(pk=run_id)
    if run.status in (AgentRun.Status.PLANNING, AgentRun.Status.RUNNING):
        run.status = AgentRun.Status.QUEUED
        run.save(update_fields=("status", "updated_at"))
    return run.status


def _complete_without_execution(run: AgentRun) -> str:
    now = timezone.now()
    run.verification_data = {
        "summary": "No approved business action was executed.",
        "citations": sorted(observed_references(run)[0])[:5],
    }
    run.status = AgentRun.Status.COMPLETED
    run.completed_at = now
    run.save(
        update_fields=("verification_data", "status", "completed_at", "updated_at")
    )
    _audit(
        actor=run.requester,
        action=actions.AGENT_RUN_COMPLETED,
        run=run,
        metadata={"executed": False},
    )
    return run.status


@transaction.atomic
def mark_agent_run_failed(*, run_id: UUID | str, failure_code: str) -> str:
    run = (
        AgentRun.objects.select_for_update()
        .select_related("project", "requester")
        .get(pk=run_id)
    )
    if run.status in TERMINAL_RUN_STATUSES:
        return run.status
    run.status = AgentRun.Status.FAILED
    run.safe_failure_code = failure_code[:64]
    run.completed_at = timezone.now()
    run.save(
        update_fields=("status", "safe_failure_code", "completed_at", "updated_at")
    )
    _audit(
        actor=run.requester,
        action=actions.AGENT_RUN_FAILED,
        run=run,
        metadata={"failure_code": run.safe_failure_code},
    )
    return run.status


def _underlying_action_allowed(actor: User, proposal: AgentProposal) -> bool:
    if proposal.action_code == AgentProposal.Action.TEAM_NOTIFICATION:
        return can_manage_project(actor, proposal.run.project)
    task_id = proposal.payload.get("task_id")
    if not isinstance(task_id, int):
        return False
    try:
        task = tasks_visible_to(actor).get(pk=task_id)
    except Task.DoesNotExist:
        return False
    project_id = task.project_id or task.course.project_id  # type: ignore[union-attr]
    if project_id != proposal.run.project_id:
        return False
    if proposal.action_code == AgentProposal.Action.TASK_COMMENT:
        return actor.has_perm("tasks.comment_task")
    if proposal.action_code == AgentProposal.Action.TASK_UPDATE:
        return can_manage_task(actor, task) or can_update_assigned_task(actor, task)
    if proposal.action_code == AgentProposal.Action.TASK_ASSIGNMENT:
        return actor.has_perm("tasks.manage_task_assignments") and can_manage_task(
            actor, task
        )
    if proposal.action_code == AgentProposal.Action.DEADLINE_CHANGE:
        return can_manage_task(actor, task)
    return False


@transaction.atomic
def decide_agent_proposal(
    *,
    actor: User,
    proposal: AgentProposal,
    approve: bool,
    reason: str,
    request: HttpRequest | None = None,
) -> AgentProposal:
    proposal = (
        AgentProposal.objects.select_for_update()
        .select_related("run", "run__project", "run__requester")
        .get(pk=proposal.pk)
    )
    if not can_decide_agent_proposal(actor, proposal):
        raise PermissionDenied(_("Proposal decision permission is required."))
    if proposal.created_at < timezone.now() - timedelta(
        hours=int(settings.PROJECT_AGENT_PROPOSAL_TTL_HOURS)
    ):
        proposal.status = AgentProposal.Status.EXPIRED
        proposal.safe_failure_code = "proposal_expired"
        proposal.save(update_fields=("status", "safe_failure_code", "updated_at"))
        _audit(
            actor=actor,
            action=actions.AGENT_PROPOSAL_EXPIRED,
            run=proposal.run,
            metadata={"proposal_id": str(proposal.pk)},
            request=request,
        )
        _verify_terminal_proposals(proposal.run)
        return proposal
    reason = " ".join(reason.split())
    if not reason or len(reason) > 500:
        raise ValidationError(_("A bounded decision reason is required."))
    if approve and not (
        actor.has_perm("project_agents.execute_agentproposal")
        and _underlying_action_allowed(actor, proposal)
    ):
        raise PermissionDenied(
            _("Current business permission is required to approve this proposal.")
        )
    proposal.approver = actor
    proposal.decision_reason = reason
    proposal.decided_at = timezone.now()
    proposal.status = (
        AgentProposal.Status.APPROVED if approve else AgentProposal.Status.REJECTED
    )
    proposal.save(
        update_fields=(
            "approver",
            "decision_reason",
            "decided_at",
            "status",
            "updated_at",
        )
    )
    _audit(
        actor=actor,
        action=actions.AGENT_PROPOSAL_APPROVED
        if approve
        else actions.AGENT_PROPOSAL_REJECTED,
        run=proposal.run,
        metadata={"proposal_id": str(proposal.pk), "action_code": proposal.action_code},
        request=request,
    )
    if approve:
        proposal.run.status = AgentRun.Status.EXECUTING
        proposal.run.save(update_fields=("status", "updated_at"))
        transaction.on_commit(partial(_enqueue_proposal, proposal.pk))
    else:
        _verify_terminal_proposals(proposal.run)
    return proposal


def _task_update_data(task: Task, *, changes: dict[str, object]) -> dict[str, object]:
    data: dict[str, object] = {
        "code": task.code,
        "project": task.project,
        "course": task.course,
        "parent": task.parent,
        "name_ar": task.name_ar,
        "name_en": task.name_en,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "start_date": task.start_date,
        "due_date": task.due_date,
        "estimated_hours": task.estimated_hours,
        "actual_hours": task.actual_hours,
        "blocking_reason": task.blocking_reason,
    }
    data.update(changes)
    return data


def _update_managed_task(
    *, actor: User, task: Task, changes: dict[str, object]
) -> Task:
    data = _task_update_data(task, changes=changes)
    return update_task(
        actor=actor,
        task=task,
        code=data["code"],
        project=data["project"],
        course=data["course"],
        parent=data["parent"],
        name_ar=data["name_ar"],
        name_en=data["name_en"],
        description=data["description"],
        status=data["status"],
        priority=data["priority"],
        start_date=data["start_date"],
        due_date=data["due_date"],
        estimated_hours=data["estimated_hours"],
        actual_hours=data["actual_hours"],
        blocking_reason=data["blocking_reason"],
    )


def _execute_task_action(actor: User, proposal: AgentProposal, task: Task) -> None:
    payload = proposal.payload
    if proposal.action_code == AgentProposal.Action.TASK_COMMENT:
        add_task_comment(actor=actor, task=task, body=str(payload["comment"]))
    elif proposal.action_code == AgentProposal.Action.TASK_ASSIGNMENT:
        ids = cast(list[int], payload["assignee_ids"])
        users = list(User.objects.filter(pk__in=ids, is_active=True))
        by_id = {user.pk: user for user in users}
        primary_id = cast(int, payload["primary_owner_id"])
        if set(by_id) != set(ids) or primary_id not in by_id:
            raise ValidationError("An approved assignee is no longer eligible.")
        replace_task_assignments(
            actor=actor,
            task=task,
            assignees=[by_id[item] for item in ids],
            primary_owner=by_id[primary_id],
        )
    elif proposal.action_code == AgentProposal.Action.DEADLINE_CHANGE:
        due_date = parse_date(str(payload["due_date"]))
        if due_date is None:
            raise ValidationError("The approved deadline is invalid.")
        _update_managed_task(
            actor=actor,
            task=task,
            changes={"due_date": due_date},
        )
    elif proposal.action_code == AgentProposal.Action.TASK_UPDATE:
        hours_raw = payload.get("actual_hours")
        hours = Decimal(str(hours_raw)) if hours_raw is not None else None
        status = str(payload["status"])
        blocking_reason = str(payload["blocking_reason"])
        if can_manage_task(actor, task):
            _update_managed_task(
                actor=actor,
                task=task,
                changes={
                    "status": status,
                    "actual_hours": hours,
                    "blocking_reason": blocking_reason,
                },
            )
        else:
            update_assigned_task(
                actor=actor,
                task=task,
                status=status,
                actual_hours=hours,
                blocking_reason=blocking_reason,
            )
    else:
        raise ValidationError("The approved task action is not supported.")


def _execute_team_notification(actor: User, proposal: AgentProposal) -> int:
    project = proposal.run.project
    if not can_manage_project(actor, project):
        raise PermissionDenied("Project management permission is required.")
    recipient_ids = set(
        project.memberships.filter(
            removed_at__isnull=True, user__is_active=True
        ).values_list("user_id", flat=True)
    )
    recipient_ids.add(project.manager_id)
    if project.supervisor_id:
        recipient_ids.add(project.supervisor_id)
    path = reverse("project_agents:detail", args=(proposal.run_id,))
    created = 0
    for recipient in User.objects.filter(pk__in=recipient_ids, is_active=True):
        notification = create_notification(
            recipient=recipient,
            message_code="agent_recovery_follow_up",
            event_key=f"agent-proposal:{proposal.pk}:{recipient.pk}",
            target_path=path,
        )
        created += notification is not None
    return created


@transaction.atomic
def _execute_approved_proposal_transactionally(*, proposal_id: UUID | str) -> str:
    proposal = (
        AgentProposal.objects.select_for_update(of=("self",))
        .select_related("run", "run__project", "run__requester", "approver")
        .get(pk=proposal_id)
    )
    if proposal.status == AgentProposal.Status.EXECUTED:
        return proposal.status
    if proposal.status not in (
        AgentProposal.Status.APPROVED,
        AgentProposal.Status.EXECUTING,
    ):
        return proposal.status
    actor = proposal.approver
    if (
        actor is None
        or not can_execute_agent_proposal(actor, proposal)
        or not _underlying_action_allowed(actor, proposal)
    ):
        proposal.status = AgentProposal.Status.FAILED
        proposal.safe_failure_code = "access_revoked"
        proposal.save(update_fields=("status", "safe_failure_code", "updated_at"))
        return _verify_terminal_proposals(proposal.run)
    current_before: dict[str, object]
    task: Task | None = None
    if proposal.action_code == AgentProposal.Action.TEAM_NOTIFICATION:
        project = Project.objects.select_for_update().get(pk=proposal.run.project_id)
        proposal.run.project = project
        current_before = _project_notification_state(project)
    else:
        task_id = proposal.payload.get("task_id")
        if not isinstance(task_id, int):
            proposal.status = AgentProposal.Status.FAILED
            proposal.safe_failure_code = "invalid_target"
            proposal.save(update_fields=("status", "safe_failure_code", "updated_at"))
            return _verify_terminal_proposals(proposal.run)
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("project", "course", "course__project", "parent")
            .get(pk=task_id)
        )
        current_before = _task_state(task)
    if _fingerprint(current_before) != proposal.before_state_fingerprint:
        proposal.status = AgentProposal.Status.STALE
        proposal.safe_failure_code = "before_state_changed"
        source_type = "project" if task is None else "task"
        source_id = proposal.run.project_id if task is None else task.pk
        proposal.execution_result = {
            "before": proposal.before_state,
            "current": current_before,
            "citation": f"{source_type}:{source_id}",
            "path": (
                reverse("projects:detail", args=(source_id,))
                if task is None
                else reverse("tasks:detail", args=(source_id,))
            ),
        }
        proposal.save(
            update_fields=(
                "status",
                "safe_failure_code",
                "execution_result",
                "updated_at",
            )
        )
        _audit(
            actor=actor,
            action=actions.AGENT_PROPOSAL_STALE,
            run=proposal.run,
            metadata={"proposal_id": str(proposal.pk)},
        )
        return _verify_terminal_proposals(proposal.run)
    proposal.status = AgentProposal.Status.EXECUTING
    proposal.save(update_fields=("status", "updated_at"))
    if task is not None:
        _execute_task_action(actor, proposal, task)
        refreshed = Task.objects.select_related(
            "project", "course", "course__project", "parent"
        ).get(pk=task.pk)
        after = _task_state(refreshed)
        citation = f"task:{refreshed.pk}"
        path = reverse("tasks:detail", args=(refreshed.pk,))
    else:
        notification_count = _execute_team_notification(actor, proposal)
        refreshed_project = Project.objects.get(pk=proposal.run.project_id)
        after = _project_notification_state(refreshed_project)
        after["notifications_created"] = notification_count
        citation = f"project:{refreshed_project.pk}"
        path = reverse("projects:detail", args=(refreshed_project.pk,))
    # Recheck again after the domain service and before commit. A concurrent
    # access revocation rolls back the write and is persisted as a safe
    # failure by the public wrapper.
    if not can_execute_agent_proposal(
        actor, proposal
    ) or not _underlying_action_allowed(actor, proposal):
        raise PermissionDenied("Project-agent execution access was revoked.")
    proposal.execution_result = {
        "before": current_before,
        "after": after,
        "citation": citation,
        "path": path,
    }
    proposal.status = AgentProposal.Status.EXECUTED
    proposal.executed_at = timezone.now()
    proposal.save(
        update_fields=("execution_result", "status", "executed_at", "updated_at")
    )
    _audit(
        actor=actor,
        action=actions.AGENT_PROPOSAL_EXECUTED,
        run=proposal.run,
        metadata={"proposal_id": str(proposal.pk), "action_code": proposal.action_code},
    )
    return _verify_terminal_proposals(proposal.run)


@transaction.atomic
def mark_agent_proposal_failed(*, proposal_id: UUID | str, failure_code: str) -> str:
    """Persist a safe terminal outcome after a rolled-back execution failure."""

    proposal = (
        AgentProposal.objects.select_for_update(of=("self",))
        .select_related("run", "run__project", "run__requester", "approver")
        .get(pk=proposal_id)
    )
    if proposal.status in (
        AgentProposal.Status.EXECUTED,
        AgentProposal.Status.STALE,
        AgentProposal.Status.EXPIRED,
        AgentProposal.Status.FAILED,
    ):
        return proposal.status
    if proposal.status not in (
        AgentProposal.Status.APPROVED,
        AgentProposal.Status.EXECUTING,
    ):
        return proposal.status
    proposal.status = AgentProposal.Status.FAILED
    proposal.safe_failure_code = failure_code[:64]
    proposal.save(update_fields=("status", "safe_failure_code", "updated_at"))
    _audit(
        actor=proposal.approver or proposal.run.requester,
        action=actions.AGENT_PROPOSAL_FAILED,
        run=proposal.run,
        metadata={
            "proposal_id": str(proposal.pk),
            "action_code": proposal.action_code,
            "failure_code": proposal.safe_failure_code,
        },
    )
    return _verify_terminal_proposals(proposal.run)


def execute_approved_proposal(*, proposal_id: UUID | str) -> str:
    """Execute once, rolling back all domain writes on an expected rejection."""

    try:
        return _execute_approved_proposal_transactionally(proposal_id=proposal_id)
    except (PermissionDenied, ValidationError, Task.DoesNotExist, Project.DoesNotExist):
        return mark_agent_proposal_failed(
            proposal_id=proposal_id,
            failure_code="domain_validation_failed",
        )


def _verify_terminal_proposals(run: AgentRun) -> str:
    run.refresh_from_db()
    active = run.proposals.filter(
        status__in=(
            AgentProposal.Status.PENDING,
            AgentProposal.Status.APPROVED,
            AgentProposal.Status.EXECUTING,
        )
    )
    if active.exists():
        return run.status
    terminal = list(run.proposals.order_by("created_at"))
    results = [
        {
            "proposal_id": str(item.pk),
            "action_code": item.action_code,
            "status": item.status,
            "citation": item.execution_result.get("citation")
            if isinstance(item.execution_result, dict)
            else None,
            "path": item.execution_result.get("path")
            if isinstance(item.execution_result, dict)
            else None,
        }
        for item in terminal
    ]
    run.status = AgentRun.Status.VERIFYING
    run.save(update_fields=("status", "updated_at"))
    if run.current_step < run.max_steps:
        _create_step(
            run=run,
            step_type=AgentStep.StepType.VERIFICATION,
            data={
                "summary": (
                    "Approved proposal outcomes were verified against current "
                    "application state."
                ),
                "results": results,
            },
        )
    run.verification_data = {
        "summary": (
            "Approved proposal outcomes were verified against current application "
            "state."
        ),
        "results": results,
    }
    if any(item.status == AgentProposal.Status.EXPIRED for item in terminal):
        run.status = AgentRun.Status.EXPIRED
        run.safe_failure_code = "proposal_expired"
    elif any(item.status == AgentProposal.Status.STALE for item in terminal):
        run.status = AgentRun.Status.STALE
    elif any(item.status == AgentProposal.Status.FAILED for item in terminal):
        run.status = AgentRun.Status.FAILED
        run.safe_failure_code = "proposal_execution_failed"
    else:
        run.status = AgentRun.Status.COMPLETED
    run.completed_at = timezone.now()
    run.save(
        update_fields=(
            "verification_data",
            "status",
            "safe_failure_code",
            "completed_at",
            "updated_at",
        )
    )
    if run.status == AgentRun.Status.COMPLETED:
        _audit(
            actor=run.requester,
            action=actions.AGENT_RUN_COMPLETED,
            run=run,
            metadata={
                "executed": any(
                    item.status == AgentProposal.Status.EXECUTED for item in terminal
                )
            },
        )
    return run.status


@transaction.atomic
def review_agent_run(
    *, actor: User, run: AgentRun, request: HttpRequest | None = None
) -> AgentMemory:
    run = (
        AgentRun.objects.select_for_update()
        .select_related("project", "requester")
        .get(pk=run.pk)
    )
    if not can_review_agent_run(actor, run):
        raise PermissionDenied(_("Project-agent review permission is required."))
    citations = sorted(observed_references(run)[0])[:10]
    summary = {
        "summary": str(run.output_data.get("summary", ""))[:2_000]
        if isinstance(run.output_data, dict)
        else "",
        "verification": run.verification_data,
    }
    now = timezone.now()
    run.reviewed_by = actor
    run.reviewed_at = now
    run.save(update_fields=("reviewed_by", "reviewed_at", "updated_at"))
    memory = AgentMemory.objects.create(
        project=run.project,
        source_run=run,
        reviewed_summary=summary,
        citations=citations,
        reviewer=actor,
        reviewed_at=now,
    )
    AgentReviewedEvent.objects.create(
        memory=memory,
        safe_payload={
            "event": "agent_run.reviewed",
            "memory_id": memory.pk,
            "run_id": str(run.pk),
            "project_code": run.project.code,
            "language": run.language,
            "reviewed_at": now.isoformat(),
            "summary": summary["summary"],
            "verification_results": [
                {
                    "action_code": str(item.get("action_code", "")),
                    "status": str(item.get("status", "")),
                    "citation": str(item.get("citation", "")),
                }
                for item in (
                    run.verification_data.get("results", [])
                    if isinstance(run.verification_data, dict)
                    else []
                )
                if isinstance(item, dict)
            ][:8],
            "citations": citations,
        },
    )
    _audit(actor=actor, action=actions.AGENT_RUN_REVIEWED, run=run, request=request)
    return memory


@transaction.atomic
def cancel_agent_run(
    *, actor: User, run: AgentRun, request: HttpRequest | None = None
) -> AgentRun:
    run = (
        AgentRun.objects.select_for_update()
        .select_related("project", "requester")
        .get(pk=run.pk)
    )
    if run.requester_id != actor.pk or run.status not in {
        AgentRun.Status.QUEUED,
        AgentRun.Status.PLANNING,
        AgentRun.Status.RUNNING,
        AgentRun.Status.AWAITING_APPROVAL,
    }:
        raise PermissionDenied(_("This project-agent run cannot be cancelled."))
    if run.proposals.exclude(status=AgentProposal.Status.PENDING).exists():
        raise ValidationError(_("A decided proposal prevents cancellation."))
    run.proposals.filter(status=AgentProposal.Status.PENDING).update(
        status=AgentProposal.Status.REJECTED,
        approver=actor,
        decision_reason="cancelled_by_requester",
        decided_at=timezone.now(),
    )
    run.status = AgentRun.Status.CANCELLED
    run.cancelled_at = timezone.now()
    run.completed_at = run.cancelled_at
    run.save(update_fields=("status", "cancelled_at", "completed_at", "updated_at"))
    _audit(actor=actor, action=actions.AGENT_RUN_CANCELLED, run=run, request=request)
    return run


def recover_stale_agent_runs() -> int:
    cutoff = timezone.now() - timedelta(
        minutes=int(settings.PROJECT_AGENT_STALE_MINUTES)
    )
    run_ids = list(
        AgentRun.objects.filter(
            status__in=(AgentRun.Status.PLANNING, AgentRun.Status.RUNNING),
            updated_at__lt=cutoff,
        ).values_list("pk", flat=True)[:100]
    )
    recovered_run_ids = [
        run_id
        for run_id in run_ids
        if _recover_stale_agent_run(run_id=run_id, cutoff=cutoff)
    ]
    for run_id in recovered_run_ids:
        _enqueue_run(run_id)
    proposal_ids = list(
        AgentProposal.objects.filter(
            status=AgentProposal.Status.PENDING,
            created_at__lt=timezone.now()
            - timedelta(hours=int(settings.PROJECT_AGENT_PROPOSAL_TTL_HOURS)),
        ).values_list("pk", flat=True)[:100]
    )
    for proposal_id in proposal_ids:
        _expire_pending_proposal(proposal_id=proposal_id)
    return len(recovered_run_ids) + len(proposal_ids)


@transaction.atomic
def _recover_stale_agent_run(*, run_id: UUID | str, cutoff: datetime) -> bool:
    run = AgentRun.objects.select_for_update().get(pk=run_id)
    if run.status not in (AgentRun.Status.PLANNING, AgentRun.Status.RUNNING):
        return False
    if run.updated_at >= cutoff:
        return False
    run.status = AgentRun.Status.QUEUED
    run.save(update_fields=("status", "updated_at"))
    return True


@transaction.atomic
def _expire_pending_proposal(*, proposal_id: UUID | str) -> str:
    proposal = (
        AgentProposal.objects.select_for_update(of=("self",))
        .select_related("run", "run__project", "run__requester")
        .get(pk=proposal_id)
    )
    if proposal.status != AgentProposal.Status.PENDING:
        return proposal.status
    if proposal.created_at >= timezone.now() - timedelta(
        hours=int(settings.PROJECT_AGENT_PROPOSAL_TTL_HOURS)
    ):
        return proposal.status
    proposal.status = AgentProposal.Status.EXPIRED
    proposal.safe_failure_code = "proposal_expired"
    proposal.save(update_fields=("status", "safe_failure_code", "updated_at"))
    _audit(
        actor=proposal.run.requester,
        action=actions.AGENT_PROPOSAL_EXPIRED,
        run=proposal.run,
        metadata={"proposal_id": str(proposal.pk)},
    )
    return _verify_terminal_proposals(proposal.run)
