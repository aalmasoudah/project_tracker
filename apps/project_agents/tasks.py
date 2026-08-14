"""Celery wrappers for bounded run, retry, execution, and recovery."""

from celery import Task, shared_task  # type: ignore[import-untyped]
from django.db import OperationalError

from apps.project_agents.integration_auth import cleanup_expired_nonces
from apps.project_agents.providers.base import TemporaryProviderError
from apps.project_agents.services import (
    execute_approved_proposal,
    mark_agent_proposal_failed,
    mark_agent_run_failed,
    process_agent_run,
    recover_stale_agent_runs,
)


@shared_task(bind=True, max_retries=8)  # type: ignore[untyped-decorator]
def process_project_agent(self: Task, run_id: str) -> str:
    try:
        return process_agent_run(run_id=run_id)
    except TemporaryProviderError as error:
        if self.request.retries >= self.max_retries:
            return mark_agent_run_failed(
                run_id=run_id, failure_code="provider_retry_exhausted"
            )
        raise self.retry(
            exc=RuntimeError("Project-agent provider is temporarily unavailable."),
            countdown=(error.retry_after_seconds or 30 * (2**self.request.retries)),
        ) from error


@shared_task(bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def execute_project_agent_proposal(self: Task, proposal_id: str) -> str:
    try:
        return execute_approved_proposal(proposal_id=proposal_id)
    except OperationalError as error:
        if self.request.retries >= self.max_retries:
            return mark_agent_proposal_failed(
                proposal_id=proposal_id,
                failure_code="execution_retry_exhausted",
            )
        raise self.retry(
            exc=RuntimeError("Project-agent execution is temporarily unavailable."),
            countdown=15 * (2**self.request.retries),
        ) from error


@shared_task  # type: ignore[untyped-decorator]
def recover_stale_project_agents() -> int:
    return recover_stale_agent_runs() + cleanup_expired_nonces()
