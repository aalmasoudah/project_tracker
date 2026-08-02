"""Permission-scoped Phase 14 archive and operations pages."""

from typing import cast

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from apps.accounts.models import User
from apps.operations.forms import ArchiveFilterForm
from apps.operations.policies import (
    BACKUP_RETENTION_DAYS,
    RETENTION_POLICY_CODE,
    RPO_HOURS,
    RTO_HOURS,
)
from apps.operations.selectors import (
    archive_entry,
    archive_types_available_to,
    archived_records_visible_to,
    latest_recorded_status,
)
from apps.operations.services import database_status


@login_required
@permission_required(
    "operations.view_operations_status",
    raise_exception=True,
)
@require_GET
def operations_status(request: HttpRequest) -> HttpResponse:
    response = render(
        request,
        "operations/status.html",
        {
            "backup": latest_recorded_status("backup"),
            "backup_retention_days": BACKUP_RETENTION_DAYS,
            "database_status": database_status(),
            "retention_policy": RETENTION_POLICY_CODE,
            "restore_test": latest_recorded_status("restore_test"),
            "rpo_hours": RPO_HOURS,
            "rto_hours": RTO_HOURS,
        },
    )
    patch_cache_control(response, no_store=True, private=True)
    return response


@login_required
@permission_required("operations.view_archive_center", raise_exception=True)
@require_GET
def archive_center(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    available_types = archive_types_available_to(actor)
    if not available_types:
        raise PermissionDenied
    data = request.GET or {"record_type": available_types[0].code}
    form = ArchiveFilterForm(actor, data)
    if not form.is_valid():
        response = render(
            request,
            "operations/archive_center.html",
            {"form": form, "page": None, "entries": ()},
            status=400,
        )
        patch_cache_control(response, no_store=True, private=True)
        return response
    record_type = form.cleaned_data["record_type"]
    records = archived_records_visible_to(
        actor,
        record_type,
        query=form.cleaned_data["query"],
    )
    page = Paginator(records, 50).get_page(request.GET.get("page"))
    language_code = (get_language() or "ar")[:2]
    entries = tuple(
        archive_entry(record_type, record, language_code) for record in page.object_list
    )
    query_parameters = request.GET.copy()
    query_parameters.pop("page", None)
    response = render(
        request,
        "operations/archive_center.html",
        {
            "entries": entries,
            "form": form,
            "page": page,
            "query_string": query_parameters.urlencode(),
        },
    )
    patch_cache_control(response, no_store=True, private=True)
    return response
