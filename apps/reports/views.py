"""Authenticated stateless report generation endpoints."""

from typing import cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import get_language
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.reports.datasets import ReportTooLargeError
from apps.reports.forms import ReportRequestForm
from apps.reports.policies import PDF, reports_available_to
from apps.reports.services import build_report_document, render_report


def _assert_report_access(actor: User) -> None:
    if not reports_available_to(actor):
        raise PermissionDenied


@login_required
@require_GET
def report_index(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    _assert_report_access(actor)
    language_code = get_language() or "ar"
    form = ReportRequestForm(actor, initial={"locale": language_code[:2]})
    return render(
        request,
        "reports/index.html",
        {"form": form, "max_rows": 5_000},
    )


@login_required
@require_POST
def report_generate(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    _assert_report_access(actor)
    form = ReportRequestForm(actor, request.POST)
    if not form.is_valid():
        return render(
            request,
            "reports/index.html",
            {"form": form, "max_rows": 5_000},
            status=400,
        )
    cleaned = form.cleaned_data
    try:
        document = build_report_document(
            actor=actor,
            report_type=cleaned["report_type"],
            project=cleaned["project"],
            course=cleaned["course"],
            start=cleaned["date_from"],
            end=cleaned["date_to"],
            language_code=cleaned["locale"],
        )
    except ReportTooLargeError as error:
        form.add_error(None, str(error))
        return render(
            request,
            "reports/index.html",
            {"form": form, "max_rows": 5_000},
            status=400,
        )
    output_format = cleaned["output_format"]
    payload = render_report(
        document,
        output_format=output_format,
        language_code=cleaned["locale"],
    )
    content_type = (
        "application/pdf"
        if output_format == PDF
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"{document.filename_stem}-{cleaned['locale']}.{output_format}"
    response = HttpResponse(payload, content_type=content_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox"
    return response
