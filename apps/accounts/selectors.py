"""Permission-scoped account query helpers."""

from django.db.models import QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.accounts.normalization import normalize_account_search


def users_visible_to(actor: User, *, search: str = "") -> QuerySet[User]:
    """Return only accounts the actor may discover."""
    queryset = User.objects.select_related("department").prefetch_related("groups")
    if actor.has_perm("accounts.manage_accounts"):
        visible = queryset
    elif actor.has_perm("accounts.view_all_directory"):
        visible = queryset.filter(is_active=True, is_superuser=False)
    elif actor.has_perm("accounts.view_department_directory"):
        if actor.department_id is None:
            visible = queryset.none()
        else:
            visible = queryset.filter(
                is_active=True,
                is_superuser=False,
                department_id=actor.department_id,
            )
    elif actor.has_perm("accounts.view_own_profile"):
        visible = queryset.filter(pk=actor.pk)
    else:
        visible = queryset.none()

    normalized_search = normalize_account_search(search)
    if normalized_search:
        visible = visible.filter(search_key__contains=normalized_search)
    return visible.order_by("display_name", "username")


def visible_user_or_404(actor: User, user_id: int) -> User:
    """Resolve a visible account without leaking inaccessible identifiers."""
    try:
        return users_visible_to(actor).get(pk=user_id)
    except User.DoesNotExist as error:
        raise Http404 from error
