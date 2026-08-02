"""Permission-scoped project query helpers."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.audit.models import AuditEvent
from apps.projects.models import Project


def projects_visible_to(
    actor: User,
    *,
    search: str = "",
    status: str = "",
    priority: str = "",
    include_archived: bool = False,
) -> QuerySet[Project]:
    """Return only projects the actor may discover."""
    queryset = Project.objects.select_related(
        "department",
        "client",
        "category",
        "manager",
        "supervisor",
    ).prefetch_related("memberships__user")
    if actor.has_perm("projects.view_all_projects"):
        visible = queryset
    elif actor.has_perm("projects.view_managed_projects"):
        visible = queryset.filter(manager=actor)
    elif actor.has_perm("projects.view_assigned_projects"):
        visible = queryset.filter(
            Q(supervisor=actor)
            | Q(memberships__user=actor, memberships__removed_at__isnull=True),
            is_archived=False,
            status=Project.Status.ACTIVE,
        )
    else:
        visible = queryset.none()

    if not include_archived or actor.has_perm("projects.view_assigned_projects"):
        visible = visible.filter(is_archived=False)
    normalized_search = normalize_account_search(search)
    if normalized_search:
        visible = visible.filter(search_key__contains=normalized_search)
    if status in Project.Status.values:
        visible = visible.filter(status=status)
    if priority in Project.Priority.values:
        visible = visible.filter(priority=priority)
    return visible.distinct().order_by("code")


def visible_project_or_404(actor: User, project_id: int) -> Project:
    """Resolve one visible project without leaking inaccessible identifiers."""
    try:
        return projects_visible_to(actor, include_archived=True).get(pk=project_id)
    except Project.DoesNotExist as error:
        raise Http404 from error


def can_manage_project(actor: User, project: Project) -> bool:
    """Return whether the actor may modify this project."""
    if (
        not actor.has_perm("projects.change_project")
        or project.is_archived
        or project.status == Project.Status.COMPLETED
    ):
        return False
    return (
        actor.has_perm("projects.view_all_projects") or project.manager_id == actor.pk
    )


def can_archive_project(actor: User, project: Project) -> bool:
    """Return whether the actor may archive or restore this project."""
    if not (
        actor.has_perm("projects.archive_project")
        and actor.has_perm("projects.restore_project")
    ):
        return False
    return (
        actor.has_perm("projects.view_all_projects") or project.manager_id == actor.pk
    )


def can_view_project_budget(actor: User, project: Project) -> bool:
    """Return whether budget may be rendered for this visible project."""
    return actor.has_perm("projects.view_project_budget") and (
        actor.has_perm("projects.view_all_projects") or project.manager_id == actor.pk
    )


def project_history_visible_to(
    actor: User,
    project: Project,
) -> QuerySet[AuditEvent]:
    """Return scoped history for one visible project."""
    if not actor.has_perm("projects.view_project_history"):
        raise PermissionDenied("Project history permission is required.")
    if not (
        actor.has_perm("projects.view_all_projects") or project.manager_id == actor.pk
    ):
        raise PermissionDenied("Project history is not visible for this project.")
    return AuditEvent.objects.select_related("actor").filter(
        scope=AuditEvent.Scope.PROJECTS,
        target_type="project",
        target_id=str(project.pk),
    )
