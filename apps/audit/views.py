"""Read-only Phase 2 audit views."""

from typing import cast

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.models import User
from apps.audit.selectors import audit_events_visible_to


@login_required
@permission_required("audit.view_auditevent", raise_exception=True)
def event_list(request: HttpRequest) -> HttpResponse:
    """Render a paginated, read-only audit stream."""
    events = audit_events_visible_to(cast(User, request.user))
    page = Paginator(events, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "audit/event_list.html",
        {"page": page},
    )
