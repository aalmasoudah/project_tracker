"""Permission-scoped department query helpers."""

from django.db.models import QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search
from apps.organizations.models import Department


def departments_visible_to(
    actor: User,
    *,
    search: str = "",
) -> QuerySet[Department]:
    """Return only departments the actor may discover."""
    queryset = Department.objects.all()
    if actor.has_perm("organizations.add_department"):
        visible = queryset
    elif actor.has_perm("organizations.view_all_departments"):
        visible = queryset.filter(is_archived=False)
    elif actor.has_perm("organizations.view_department"):
        if actor.department_id is None:
            visible = queryset.none()
        else:
            visible = queryset.filter(
                pk=actor.department_id,
                is_archived=False,
            )
    else:
        visible = queryset.none()

    normalized_search = normalize_account_search(search)
    if normalized_search:
        visible = visible.filter(search_key__contains=normalized_search)
    return visible.order_by("code")


def visible_department_or_404(actor: User, department_id: int) -> Department:
    """Resolve a department without exposing inaccessible records."""
    try:
        return departments_visible_to(actor).get(pk=department_id)
    except Department.DoesNotExist as error:
        raise Http404 from error
