"""Pure Phase 7 milestone policy and progress tests."""

from decimal import Decimal

import pytest

from apps.approvals.models import Milestone
from apps.approvals.policies import MILESTONE_STATUS_TRANSITIONS
from apps.progress.calculations import ProgressState
from apps.progress.services import calculate_milestone_progress


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (Milestone.Status.DRAFT, Decimal("0.00")),
        (Milestone.Status.IN_PROGRESS, Decimal("0.00")),
        (Milestone.Status.PENDING_APPROVAL, Decimal("0.00")),
        (Milestone.Status.COMPLETED, Decimal("100.00")),
    ],
)
def test_milestone_progress_is_approval_status_based(
    status: str,
    expected: Decimal,
) -> None:
    milestone = Milestone(status=status, is_archived=False)

    result = calculate_milestone_progress(milestone)

    assert result.state == ProgressState.VALUE
    assert result.percentage == expected


def test_cancelled_and_archived_milestones_are_excluded() -> None:
    cancelled = calculate_milestone_progress(
        Milestone(status=Milestone.Status.CANCELLED)
    )
    archived = calculate_milestone_progress(
        Milestone(status=Milestone.Status.COMPLETED, is_archived=True)
    )

    assert cancelled.state == ProgressState.EXCLUDED
    assert archived.state == ProgressState.EXCLUDED


def test_only_approval_service_can_reach_terminal_milestone_status() -> None:
    assert MILESTONE_STATUS_TRANSITIONS[Milestone.Status.DRAFT] == (
        Milestone.Status.IN_PROGRESS,
        Milestone.Status.CANCELLED,
    )
    assert (
        Milestone.Status.PENDING_APPROVAL
        not in MILESTONE_STATUS_TRANSITIONS[Milestone.Status.IN_PROGRESS]
    )
    assert MILESTONE_STATUS_TRANSITIONS[Milestone.Status.PENDING_APPROVAL] == ()
    assert MILESTONE_STATUS_TRANSITIONS[Milestone.Status.COMPLETED] == ()
