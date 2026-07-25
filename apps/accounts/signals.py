"""Integrity checks for managed role assignments."""

from typing import Any

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.roles import ROLE_CODES


@receiver(m2m_changed, sender=User.groups.through)
def prevent_multiple_managed_roles(
    sender: type[Any],
    instance: User | Group,
    action: str,
    reverse: bool,
    pk_set: set[int] | None,
    **kwargs: Any,
) -> None:
    """Reject ORM operations that would assign more than one managed role."""
    del sender, kwargs
    if action != "pre_add" or not pk_set:
        return

    if reverse:
        group = instance
        if not isinstance(group, Group) or group.name not in ROLE_CODES:
            return
        users = User.objects.filter(pk__in=pk_set, groups__name__in=ROLE_CODES)
        if users.exists():
            raise ValidationError(_("An account can have only one managed role."))
        return

    user = instance
    if not isinstance(user, User):
        return
    added_managed_count = Group.objects.filter(
        pk__in=pk_set,
        name__in=ROLE_CODES,
    ).count()
    existing_managed_count = user.groups.filter(name__in=ROLE_CODES).count()
    if added_managed_count + existing_managed_count > 1:
        raise ValidationError(_("An account can have only one managed role."))
