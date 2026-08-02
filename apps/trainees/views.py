"""Thin Phase 8 views."""

import csv
from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.trainees.forms import (
    DuplicateResolutionForm,
    EnrollmentForm,
    ImportUploadForm,
)
from apps.trainees.models import ImportRow
from apps.trainees.selectors import (
    can_archive_enrollment,
    can_manage_enrollment,
    enrollments_visible_to,
    import_batches_visible_to,
    visible_batch_or_404,
    visible_enrollment_or_404,
)
from apps.trainees.services import (
    cancel_import,
    confirm_import,
    create_enrollment,
    preview_import,
    set_enrollment_archived,
    update_enrollment,
)


@login_required
@permission_required("trainees.view_courseenrollment", raise_exception=True)
def enrollment_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    page = Paginator(
        enrollments_visible_to(
            actor,
            search=request.GET.get("q", ""),
            include_archived=request.GET.get("archived") == "1",
        ),
        25,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "trainees/enrollment_list.html",
        {
            "page": page,
            "search": request.GET.get("q", ""),
            "include_archived": request.GET.get("archived") == "1",
            "show_contact": actor.has_perm("trainees.view_trainee_contact"),
        },
    )


@login_required
def enrollment_detail(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    enrollment = visible_enrollment_or_404(actor, enrollment_id)
    return render(
        request,
        "trainees/enrollment_detail.html",
        {
            "enrollment": enrollment,
            "show_contact": actor.has_perm("trainees.view_trainee_contact"),
            "can_manage": can_manage_enrollment(actor, enrollment.course)
            and not enrollment.is_archived,
            "can_archive": can_archive_enrollment(actor, enrollment),
        },
    )


@login_required
@permission_required("trainees.add_courseenrollment", raise_exception=True)
@require_http_methods(["GET", "POST"])
def enrollment_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = EnrollmentForm(request.POST or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            enrollment = create_enrollment(
                actor=actor, request=request, **form.cleaned_data
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Trainee enrolled successfully."))
            return redirect("trainees:detail", enrollment_id=enrollment.pk)
    return render(
        request,
        "trainees/enrollment_form.html",
        {"form": form, "page_title": _("Enroll trainee")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def enrollment_update(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    enrollment = visible_enrollment_or_404(actor, enrollment_id)
    if enrollment.is_archived or not can_manage_enrollment(actor, enrollment.course):
        raise PermissionDenied
    form = EnrollmentForm(request.POST or None, actor=actor, enrollment=enrollment)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        data.pop("course", None)
        try:
            enrollment = update_enrollment(
                actor=actor, enrollment=enrollment, request=request, **data
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Trainee updated successfully."))
            return redirect("trainees:detail", enrollment_id=enrollment.pk)
    return render(
        request,
        "trainees/enrollment_form.html",
        {
            "form": form,
            "page_title": _("Edit trainee"),
            "enrollment": enrollment,
        },
    )


@login_required
@require_POST
def enrollment_archive(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    enrollment = visible_enrollment_or_404(actor, enrollment_id)
    set_enrollment_archived(
        actor=actor, enrollment=enrollment, archived=True, request=request
    )
    messages.success(request, _("Trainee archived successfully."))
    return redirect("trainees:detail", enrollment_id=enrollment.pk)


@login_required
@require_POST
def enrollment_restore(request: HttpRequest, enrollment_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    enrollment = visible_enrollment_or_404(actor, enrollment_id)
    try:
        set_enrollment_archived(
            actor=actor, enrollment=enrollment, archived=False, request=request
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, _("Trainee restored successfully."))
    return redirect("trainees:detail", enrollment_id=enrollment.pk)


@login_required
@permission_required("trainees.import_trainees", raise_exception=True)
@require_http_methods(["GET", "POST"])
def import_upload(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = ImportUploadForm(request.POST or None, request.FILES or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            batch = preview_import(
                actor=actor,
                course=form.cleaned_data["course"],
                upload=form.cleaned_data["file"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(
                request, _("Import preview created. No trainees were saved.")
            )
            return redirect("trainees:import-preview", batch_id=batch.pk)
    return render(request, "trainees/import_upload.html", {"form": form})


@login_required
@permission_required("trainees.view_import_history", raise_exception=True)
def import_history(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    page = Paginator(import_batches_visible_to(actor), 25).get_page(
        request.GET.get("page")
    )
    return render(request, "trainees/import_history.html", {"page": page})


@login_required
@permission_required("trainees.view_import_history", raise_exception=True)
@require_http_methods(["GET", "POST"])
def import_preview(request: HttpRequest, batch_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    batch = visible_batch_or_404(actor, batch_id)
    rows = list(batch.rows.select_related("duplicate_enrollment__trainee"))
    duplicates = [
        row for row in rows if row.classification == ImportRow.Classification.DUPLICATE
    ]
    form = DuplicateResolutionForm(request.POST or None, rows=duplicates)
    if request.method == "POST" and form.is_valid():
        try:
            confirm_import(
                actor=actor,
                batch=batch,
                resolutions=form.resolutions(),
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Import confirmed successfully."))
            return redirect("trainees:import-preview", batch_id=batch.pk)
    return render(
        request,
        "trainees/import_preview.html",
        {"batch": batch, "rows": rows, "form": form},
    )


@login_required
@require_POST
def import_cancel(request: HttpRequest, batch_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    batch = visible_batch_or_404(actor, batch_id)
    cancel_import(actor=actor, batch=batch, request=request)
    messages.success(request, _("Import cancelled."))
    return redirect("trainees:import-preview", batch_id=batch.pk)


@login_required
def sample_csv(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    if not actor.has_perm("trainees.import_trainees"):
        raise PermissionDenied
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="trainee_import_sample.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["full_name", "phone", "email"])
    writer.writerow(["Fictional Trainee", "+966500000001", "trainee@example.test"])
    return response
