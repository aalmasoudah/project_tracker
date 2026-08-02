"""Stable Phase 7 milestone and approval policy constants."""

from typing import Final

from apps.approvals.models import ApprovalRequest, Milestone

MILESTONE_STATUS_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    Milestone.Status.DRAFT: (
        Milestone.Status.IN_PROGRESS,
        Milestone.Status.CANCELLED,
    ),
    Milestone.Status.IN_PROGRESS: (Milestone.Status.CANCELLED,),
    Milestone.Status.PENDING_APPROVAL: (),
    Milestone.Status.COMPLETED: (),
    Milestone.Status.CANCELLED: (Milestone.Status.DRAFT,),
}

PENDING_APPROVAL_STATUSES: Final = (
    ApprovalRequest.Status.PENDING_SUPERVISOR,
    ApprovalRequest.Status.PENDING_MANAGER,
)
