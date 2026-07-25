"""Transactional department lifecycle services."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.services import record_audit_event
from apps.organizations.models import Department


def _require_permission(actor: User, permission: str) -> None:
    if not actor.has_perm(permission):
        raise PermissionDenied(_("Department administration permission is required."))


@transaction.atomic
def create_department(
    *,
    actor: User,
    code: str,
    name_ar: str,
    name_en: str,
    request: HttpRequest | None = None,
) -> Department:
    """Create a bilingual active department."""
    _require_permission(actor, "organizations.add_department")
    department = Department.objects.create(
        code=code,
        name_ar=name_ar,
        name_en=name_en,
    )
    record_audit_event(
        actor=actor,
        action=actions.DEPARTMENT_CREATED,
        target_type="department",
        target_id=str(department.pk),
        target_label=department.code,
        request=request,
    )
    return department


@transaction.atomic
def update_department(
    *,
    actor: User,
    department: Department,
    name_ar: str,
    name_en: str,
    request: HttpRequest | None = None,
) -> Department:
    """Update names while keeping the stable code immutable."""
    _require_permission(actor, "organizations.change_department")
    department = Department.objects.select_for_update().get(pk=department.pk)
    changed_fields: list[str] = []
    for field_name, value in (("name_ar", name_ar), ("name_en", name_en)):
        if getattr(department, field_name) != value:
            setattr(department, field_name, value)
            changed_fields.append(field_name)
    if changed_fields:
        department.save()
        record_audit_event(
            actor=actor,
            action=actions.DEPARTMENT_UPDATED,
            target_type="department",
            target_id=str(department.pk),
            target_label=department.code,
            metadata={"changed_fields": changed_fields},
            request=request,
        )
    return department


@transaction.atomic
def archive_department(
    *,
    actor: User,
    department: Department,
    request: HttpRequest | None = None,
) -> Department:
    """Archive an empty department while preserving its stable identity."""
    _require_permission(actor, "organizations.archive_department")
    department = Department.objects.select_for_update().get(pk=department.pk)
    if department.is_archived:
        return department
    if department.users.filter(is_active=True).exists():
        raise ValidationError(
            _("Move or deactivate active users before archiving this department.")
        )
    department.is_archived = True
    department.archived_at = timezone.now()
    department.save(update_fields=("is_archived", "archived_at", "updated_at"))
    record_audit_event(
        actor=actor,
        action=actions.DEPARTMENT_ARCHIVED,
        target_type="department",
        target_id=str(department.pk),
        target_label=department.code,
        request=request,
    )
    return department


@transaction.atomic
def restore_department(
    *,
    actor: User,
    department: Department,
    request: HttpRequest | None = None,
) -> Department:
    """Restore an archived department."""
    _require_permission(actor, "organizations.restore_department")
    department = Department.objects.select_for_update().get(pk=department.pk)
    if not department.is_archived:
        return department
    department.is_archived = False
    department.archived_at = None
    department.save(update_fields=("is_archived", "archived_at", "updated_at"))
    record_audit_event(
        actor=actor,
        action=actions.DEPARTMENT_RESTORED,
        target_type="department",
        target_id=str(department.pk),
        target_label=department.code,
        request=request,
    )
    return department
