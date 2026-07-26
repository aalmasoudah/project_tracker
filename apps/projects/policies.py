"""Stable Phase 3 lifecycle policy definitions."""

from apps.projects.models import Project

STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    Project.Status.DRAFT: (Project.Status.ACTIVE, Project.Status.CANCELLED),
    Project.Status.ACTIVE: (Project.Status.ON_HOLD, Project.Status.CANCELLED),
    Project.Status.ON_HOLD: (Project.Status.ACTIVE, Project.Status.CANCELLED),
    Project.Status.CANCELLED: (Project.Status.DRAFT,),
}
