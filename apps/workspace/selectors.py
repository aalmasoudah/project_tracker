"""Owner-scoped saved-filter access."""

from django.db.models import QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.workspace.models import SavedFilter


def saved_filters_visible_to(owner: User) -> QuerySet[SavedFilter]:
    return SavedFilter.objects.filter(owner=owner).order_by("view_type", "name", "pk")


def visible_saved_filter_or_404(owner: User, filter_id: int) -> SavedFilter:
    try:
        return saved_filters_visible_to(owner).get(pk=filter_id)
    except SavedFilter.DoesNotExist as error:
        raise Http404 from error
