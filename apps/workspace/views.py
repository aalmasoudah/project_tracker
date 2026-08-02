"""Thin authenticated Phase 12 views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.workspace.forms import (
    PlanningFilterForm,
    SavedFilterForm,
    SearchForm,
    criteria_from_cleaned_data,
)
from apps.workspace.selectors import (
    saved_filters_visible_to,
    visible_saved_filter_or_404,
)
from apps.workspace.services import (
    PlanningItem,
    SearchSection,
    dashboard_context,
    global_search,
    kanban_columns,
    planning_items,
    save_filter,
    saved_filter_url,
)


@login_required
@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    context = dashboard_context(actor, get_language() or "ar")
    return render(request, "workspace/dashboard.html", context)


@login_required
@require_GET
def search(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = SearchForm(request.GET)
    sections: tuple[SearchSection, ...] = ()
    if form.is_valid() and form.cleaned_data["q"]:
        sections = global_search(actor, form.cleaned_data["q"])
    return render(
        request,
        "workspace/search.html",
        {"form": form, "sections": sections, "view_type": "search"},
    )


@login_required
@require_GET
def kanban(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = SearchForm(request.GET)
    query = form.cleaned_data["q"] if form.is_valid() else ""
    return render(
        request,
        "workspace/kanban.html",
        {
            "form": form,
            "columns": kanban_columns(actor, query),
            "view_type": "kanban",
        },
    )


def _planning_view(
    request: HttpRequest,
    *,
    template_name: str,
    title: str,
    view_type: str,
    include_sessions: bool = False,
    include_progress: bool = False,
) -> HttpResponse:
    actor = cast(User, request.user)
    form = PlanningFilterForm(request.GET)
    items: tuple[PlanningItem, ...] = ()
    if form.is_valid():
        items = planning_items(
            actor,
            language_code=get_language() or "ar",
            start=form.cleaned_data["date_from"],
            end=form.cleaned_data["date_to"],
            query=form.cleaned_data["q"],
            include_sessions=include_sessions,
            include_progress=include_progress,
        )
    return render(
        request,
        template_name,
        {
            "form": form,
            "items": items,
            "page_title": title,
            "view_type": view_type,
            "read_only": True,
        },
    )


@login_required
@require_GET
def calendar(request: HttpRequest) -> HttpResponse:
    return _planning_view(
        request,
        template_name="workspace/calendar.html",
        title=str(_("Calendar")),
        view_type="calendar",
        include_sessions=True,
    )


@login_required
@require_GET
def timeline(request: HttpRequest) -> HttpResponse:
    return _planning_view(
        request,
        template_name="workspace/planning.html",
        title=str(_("Timeline")),
        view_type="timeline",
    )


@login_required
@require_GET
def gantt(request: HttpRequest) -> HttpResponse:
    return _planning_view(
        request,
        template_name="workspace/planning.html",
        title=str(_("Gantt")),
        view_type="gantt",
        include_progress=True,
    )


@login_required
@require_GET
def saved_filter_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    return render(
        request,
        "workspace/saved_filter_list.html",
        {"saved_filters": saved_filters_visible_to(actor)},
    )


@login_required
@require_POST
def saved_filter_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = SavedFilterForm(request.POST)
    if form.is_valid():
        try:
            save_filter(
                owner=actor,
                name=form.cleaned_data["name"],
                view_type=form.cleaned_data["view_type"],
                criteria=criteria_from_cleaned_data(form.cleaned_data),
            )
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, _("Filter saved."))
    else:
        messages.error(request, _("The filter could not be saved."))
    next_path = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_path,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_path = reverse("workspace:filters")
    return redirect(next_path)


@login_required
@require_GET
def saved_filter_use(request: HttpRequest, filter_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    saved_filter = visible_saved_filter_or_404(actor, filter_id)
    return redirect(saved_filter_url(saved_filter))


@login_required
@require_POST
def saved_filter_delete(request: HttpRequest, filter_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    saved_filter = visible_saved_filter_or_404(actor, filter_id)
    saved_filter.delete()
    messages.success(request, _("Saved filter deleted."))
    return redirect("workspace:filters")
