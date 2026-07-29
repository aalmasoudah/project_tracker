"""Transactional Phase 3 project lifecycle services."""

from collections.abc import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.roles import CONTRACTOR, EMPLOYEE, PROJECT_MANAGER, SUPERVISOR
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event
from apps.courses.models import Course
from apps.projects.models import Category, Client, Project, ProjectMembership
from apps.projects.policies import STATUS_TRANSITIONS
from apps.projects.selectors import can_archive_project, can_manage_project


def _project_event(
    *,
    actor: User,
    action: str,
    project: Project,
    metadata: dict[str, object] | None = None,
    request: HttpRequest | None = None,
) -> None:
    record_audit_event(
        actor=actor,
        action=action,
        target_type="project",
        target_id=str(project.pk),
        target_label=project.code,
        metadata=metadata,
        request=request,
        scope=AuditEvent.Scope.PROJECTS,
    )


def _validate_project_people(
    project: Project,
    members: Iterable[User] = (),
) -> None:
    if project.department.is_archived:
        raise ValidationError(_("Archived departments cannot own projects."))
    if project.client is not None and project.client.is_archived:
        raise ValidationError(_("Archived clients cannot be assigned."))
    if project.category is not None and project.category.is_archived:
        raise ValidationError(_("Archived categories cannot be assigned."))
    if (
        not project.manager.is_active
        or project.manager.department_id != project.department_id
        or not project.manager.groups.filter(name=PROJECT_MANAGER).exists()
    ):
        raise ValidationError(_("Select an eligible Project Manager."))
    if project.supervisor is not None and (
        not project.supervisor.is_active
        or project.supervisor.department_id != project.department_id
        or not project.supervisor.groups.filter(name=SUPERVISOR).exists()
    ):
        raise ValidationError(_("Select an eligible Supervisor."))
    eligible = {PROJECT_MANAGER, SUPERVISOR, EMPLOYEE, CONTRACTOR}
    for member in members:
        if member.pk in {project.manager_id, project.supervisor_id}:
            raise ValidationError(
                _("Manager and supervisor are assigned separately from team members.")
            )
        if (
            not member.is_active
            or member.department_id != project.department_id
            or not member.groups.filter(name__in=eligible).exists()
        ):
            raise ValidationError(_("Every team member must be eligible and active."))


@transaction.atomic
def create_project(
    *,
    actor: User,
    request: HttpRequest | None = None,
    **data: object,
) -> Project:
    """Create a draft project inside the actor's approved boundary."""
    if not actor.has_perm("projects.add_project"):
        raise PermissionDenied(_("Project creation permission is required."))
    raw_code = data.get("code")
    if isinstance(raw_code, str):
        data["code"] = raw_code.strip().upper()
    project = Project(**data, created_by=actor, updated_by=actor)
    if not actor.has_perm("projects.view_all_projects"):
        if (
            project.manager_id != actor.pk
            or project.department_id != actor.department_id
        ):
            raise PermissionDenied(
                _("Project Managers may create only their own projects.")
            )
    if project.status != Project.Status.DRAFT:
        raise ValidationError(_("New projects must start as Draft."))
    _validate_project_people(project)
    project.full_clean()
    project.save()
    _project_event(
        actor=actor,
        action=actions.PROJECT_CREATED,
        project=project,
        request=request,
    )
    return project


@transaction.atomic
def update_project(
    *,
    actor: User,
    project: Project,
    request: HttpRequest | None = None,
    **data: object,
) -> Project:
    """Update a visible mutable project with transition enforcement."""
    project = Project.objects.select_for_update().get(pk=project.pk)
    from apps.approvals.services import has_pending_approval

    if has_pending_approval(project):
        raise ValidationError(_("Pending approval prevents project changes."))
    if not can_manage_project(actor, project):
        raise PermissionDenied(_("Project update permission is required."))
    previous_status = project.status
    if data.get("code") != project.code:
        raise ValidationError(_("Project codes cannot be changed."))
    if not actor.has_perm("projects.view_all_projects"):
        if data.get("manager") != actor or data.get("department") != project.department:
            raise PermissionDenied(
                _("Project Managers cannot transfer project ownership.")
            )
    for field_name, value in data.items():
        setattr(project, field_name, value)
    if (
        previous_status == Project.Status.ACTIVE
        and project.status != Project.Status.ACTIVE
        and Course.objects.filter(
            project=project,
            is_archived=False,
            status=Course.Status.ACTIVE,
        ).exists()
    ):
        raise ValidationError(
            _(
                "Place active courses on hold or cancel them before changing "
                "the project."
            )
        )
    if (
        project.status != previous_status
        and project.status not in STATUS_TRANSITIONS[previous_status]
    ):
        raise ValidationError(_("This project status transition is not allowed."))
    _validate_project_people(project)
    project.updated_by = actor
    project.full_clean()
    project.save()
    action = (
        actions.PROJECT_STATUS_CHANGED
        if project.status != previous_status
        else actions.PROJECT_UPDATED
    )
    _project_event(
        actor=actor,
        action=action,
        project=project,
        metadata={"previous_status": previous_status, "status": project.status},
        request=request,
    )
    return project


@transaction.atomic
def archive_project(
    *, actor: User, project: Project, request: HttpRequest | None = None
) -> Project:
    from apps.tasks.models import Task

    project = Project.objects.select_for_update().get(pk=project.pk)
    from apps.approvals.services import has_pending_approval

    if has_pending_approval(project):
        raise ValidationError(_("Pending approval prevents project archiving."))
    if not can_archive_project(actor, project):
        raise PermissionDenied(_("Project archive permission is required."))
    if Course.objects.filter(project=project, is_archived=False).exists():
        raise ValidationError(_("Archive every course before archiving this project."))
    if Task.objects.filter(project=project, is_archived=False).exists():
        raise ValidationError(
            _("Archive every project task before archiving this project.")
        )
    if not project.is_archived:
        project.is_archived = True
        project.archived_at = timezone.now()
        project.archived_by = actor
        project.updated_by = actor
        project.save(
            update_fields=(
                "is_archived",
                "archived_at",
                "archived_by",
                "updated_by",
                "updated_at",
            )
        )
        _project_event(
            actor=actor,
            action=actions.PROJECT_ARCHIVED,
            project=project,
            request=request,
        )
    return project


@transaction.atomic
def restore_project(
    *, actor: User, project: Project, request: HttpRequest | None = None
) -> Project:
    project = Project.objects.select_for_update().get(pk=project.pk)
    if not can_archive_project(actor, project):
        raise PermissionDenied(_("Project restore permission is required."))
    if (project.client and project.client.is_archived) or (
        project.category and project.category.is_archived
    ):
        raise ValidationError(_("Restore archived client or category first."))
    if project.is_archived:
        project.is_archived = False
        project.archived_at = None
        project.archived_by = None
        project.updated_by = actor
        project.save(
            update_fields=(
                "is_archived",
                "archived_at",
                "archived_by",
                "updated_by",
                "updated_at",
            )
        )
        _project_event(
            actor=actor,
            action=actions.PROJECT_RESTORED,
            project=project,
            request=request,
        )
    return project


@transaction.atomic
def replace_project_team(
    *,
    actor: User,
    project: Project,
    members: Iterable[User],
    request: HttpRequest | None = None,
) -> None:
    project = Project.objects.select_for_update().get(pk=project.pk)
    if not (
        actor.has_perm("projects.manage_project_team")
        and can_manage_project(actor, project)
    ):
        raise PermissionDenied(_("Project team permission is required."))
    member_list = list(members)
    _validate_project_people(project, member_list)
    requested_ids = {member.pk for member in member_list}
    active = ProjectMembership.objects.select_for_update().filter(
        project=project,
        removed_at__isnull=True,
    )
    current_ids = set(active.values_list("user_id", flat=True))
    now = timezone.now()
    active.exclude(user_id__in=requested_ids).update(removed_by=actor, removed_at=now)
    for member in member_list:
        if member.pk not in current_ids:
            ProjectMembership.objects.create(
                project=project,
                user=member,
                added_by=actor,
            )
    if requested_ids != current_ids:
        _project_event(
            actor=actor,
            action=actions.PROJECT_TEAM_UPDATED,
            project=project,
            metadata={
                "added_user_ids": sorted(requested_ids - current_ids),
                "removed_user_ids": sorted(current_ids - requested_ids),
            },
            request=request,
        )


def _reference_permission(model: type[Client] | type[Category], action: str) -> str:
    return f"projects.{action}_{model._meta.model_name}"


@transaction.atomic
def save_reference(
    *,
    actor: User,
    model: type[Client] | type[Category],
    code: str,
    name_ar: str,
    name_en: str,
    instance: Client | Category | None = None,
    request: HttpRequest | None = None,
) -> Client | Category:
    action_name = "change" if instance else "add"
    if not actor.has_perm(_reference_permission(model, action_name)):
        raise PermissionDenied(_("Reference administration permission is required."))
    reference = (
        model.objects.select_for_update().get(pk=instance.pk)
        if instance is not None
        else model()
    )
    if reference.is_archived:
        raise ValidationError(_("Archived reference records are read-only."))
    if instance is not None and code.strip().upper() != reference.code:
        raise ValidationError(_("Reference codes cannot be changed."))
    reference.code = code.strip().upper()
    reference.name_ar = name_ar
    reference.name_en = name_en
    reference.full_clean()
    reference.save()
    prefix = "client" if model is Client else "category"
    event_action = getattr(
        actions,
        f"{prefix.upper()}_{'UPDATED' if instance else 'CREATED'}",
    )
    record_audit_event(
        actor=actor,
        action=event_action,
        target_type=prefix,
        target_id=str(reference.pk),
        target_label=reference.code,
        request=request,
        scope=AuditEvent.Scope.PROJECTS,
    )
    return reference


@transaction.atomic
def set_reference_archived(
    *,
    actor: User,
    reference: Client | Category,
    archived: bool,
    request: HttpRequest | None = None,
) -> None:
    model = type(reference)
    permission = "archive" if archived else "restore"
    if not actor.has_perm(_reference_permission(model, permission)):
        raise PermissionDenied(_("Reference archive permission is required."))
    reference = model.objects.select_for_update().get(pk=reference.pk)
    if archived and reference.projects.filter(is_archived=False).exists():
        raise ValidationError(_("Active projects still use this record."))
    if reference.is_archived == archived:
        return
    reference.is_archived = archived
    reference.archived_at = timezone.now() if archived else None
    reference.save(update_fields=("is_archived", "archived_at", "updated_at"))
    prefix = "client" if model is Client else "category"
    event_action = getattr(
        actions,
        f"{prefix.upper()}_{'ARCHIVED' if archived else 'RESTORED'}",
    )
    record_audit_event(
        actor=actor,
        action=event_action,
        target_type=prefix,
        target_id=str(reference.pk),
        target_label=reference.code,
        request=request,
        scope=AuditEvent.Scope.PROJECTS,
    )
