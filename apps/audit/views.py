"""Permission-scoped Phase 14 audit views and bounded CSV export."""

import csv
from io import StringIO
from typing import Any, cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.forms import AuditFilterForm, default_audit_filter_data
from apps.audit.models import AuditEvent
from apps.audit.policies import MAX_AUDIT_EXPORT_ROWS
from apps.audit.presentation import action_label
from apps.audit.selectors import (
    audit_events_visible_to,
    can_export_audit,
    permitted_audit_scopes,
    safe_audit_metadata,
    visible_audit_event_or_404,
)
from apps.audit.services import record_audit_event
from apps.reports.dates import format_dual_date
from apps.reports.renderers import safe_spreadsheet_value


@login_required
@require_GET
def event_list(request: HttpRequest) -> HttpResponse:
    """Render a filtered, paginated, read-only audit stream."""
    actor = cast(User, request.user)
    if not permitted_audit_scopes(actor):
        raise PermissionDenied
    data = request.GET if request.GET else default_audit_filter_data()
    form = AuditFilterForm(actor, data)
    if not form.is_valid():
        response = render(
            request,
            "audit/event_list.html",
            {"form": form, "page": None},
            status=400,
        )
        patch_cache_control(response, no_store=True, private=True)
        return response
    events = audit_events_visible_to(actor, **_selector_kwargs(form.cleaned_data))
    page = Paginator(events, 50).get_page(request.GET.get("page"))
    query_parameters = request.GET.copy()
    query_parameters.pop("page", None)
    export_fields = {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in _selector_kwargs(form.cleaned_data).items()
        if value not in ("", None)
    }
    response = render(
        request,
        "audit/event_list.html",
        {
            "can_export": can_export_audit(actor, _requested_scopes(actor, form)),
            "export_fields": export_fields,
            "form": form,
            "page": page,
            "query_string": query_parameters.urlencode(),
        },
    )
    patch_cache_control(response, no_store=True, private=True)
    return response


@login_required
@require_GET
def event_detail(request: HttpRequest, event_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    event = visible_audit_event_or_404(actor, event_id)
    response = render(
        request,
        "audit/event_detail.html",
        {
            "event": event,
            "metadata": safe_audit_metadata(event),
            "show_ip": (
                event.scope == AuditEvent.Scope.SECURITY
                and actor.has_perm("audit.view_security_audit")
            ),
        },
    )
    patch_cache_control(response, no_store=True, private=True)
    return response


@login_required
@require_POST
def event_export(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    if not permitted_audit_scopes(actor):
        raise PermissionDenied
    form = AuditFilterForm(actor, request.POST)
    if not form.is_valid():
        response = render(
            request,
            "audit/event_list.html",
            {"form": form, "page": None},
            status=400,
        )
        patch_cache_control(response, no_store=True, private=True)
        return response
    scopes = _requested_scopes(actor, form)
    if not can_export_audit(actor, scopes):
        raise PermissionDenied
    events = list(
        audit_events_visible_to(actor, **_selector_kwargs(form.cleaned_data))[
            : MAX_AUDIT_EXPORT_ROWS + 1
        ]
    )
    if len(events) > MAX_AUDIT_EXPORT_ROWS:
        form.add_error(
            None,
            _("Narrow the filters to %(rows)s audit rows or fewer.")
            % {"rows": MAX_AUDIT_EXPORT_ROWS},
        )
        response = render(
            request,
            "audit/event_list.html",
            {"form": form, "page": None},
            status=400,
        )
        patch_cache_control(response, no_store=True, private=True)
        return response
    payload = _render_csv(events)
    selected = form.cleaned_data
    record_audit_event(
        actor=actor,
        action=actions.AUDIT_EXPORTED,
        target_type="audit_export",
        target_label=",".join(scopes),
        metadata={
            "rows": len(events),
            "filters": {
                key: (value.isoformat() if hasattr(value, "isoformat") else value)
                for key, value in _selector_kwargs(selected).items()
                if key != "query" and value not in ("", None)
            },
        },
        request=request,
        scope=AuditEvent.Scope.OPERATIONS,
    )
    filename = f"audit-export-{timezone.localdate():%Y%m%d}.csv"
    response = HttpResponse(
        payload,
        content_type="text/csv; charset=utf-8",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Content-Security-Policy"] = "sandbox"
    response.headers["X-Content-Type-Options"] = "nosniff"
    patch_cache_control(response, no_store=True, private=True)
    return response


def _selector_kwargs(cleaned: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": cleaned.get("scope", ""),
        "action": cleaned.get("action", ""),
        "target_type": cleaned.get("target_type", ""),
        "query": cleaned.get("query", ""),
        "correlation_id": cleaned.get("correlation_id", ""),
        "date_from": cleaned.get("date_from"),
        "date_to": cleaned.get("date_to"),
    }


def _requested_scopes(
    actor: User,
    form: AuditFilterForm,
) -> tuple[str, ...]:
    selected = cast(str, form.cleaned_data.get("scope", ""))
    return (selected,) if selected else permitted_audit_scopes(actor)


def _render_csv(events: list[AuditEvent]) -> str:
    stream = StringIO(newline="")
    stream.write("\ufeff")
    writer = csv.writer(stream)
    writer.writerow(
        (
            _("Time"),
            _("Scope"),
            _("Action code"),
            _("Action"),
            _("Actor"),
            _("Target type"),
            _("Target"),
            _("Correlation ID"),
        )
    )
    language_code = (get_language() or "ar")[:2]
    for event in events:
        local_time = timezone.localtime(event.created_at)
        writer.writerow(
            tuple(
                safe_spreadsheet_value(str(value))
                for value in (
                    (
                        f"{format_dual_date(local_time.date(), language_code)} "
                        f"{local_time:%H:%M}"
                    ),
                    event.scope,
                    event.action,
                    action_label(event.action),
                    event.actor.display_name if event.actor else "",
                    event.target_type,
                    event.target_label or event.target_id,
                    event.correlation_id,
                )
            )
        )
    return stream.getvalue()
