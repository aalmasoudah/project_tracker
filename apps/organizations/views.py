"""Thin department views backed by approved services and selectors."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.organizations.forms import DepartmentForm
from apps.organizations.models import Department
from apps.organizations.selectors import departments_visible_to
from apps.organizations.services import (
    archive_department,
    create_department,
    restore_department,
    update_department,
)


@login_required
def department_list(request: HttpRequest) -> HttpResponse:
    """Render only departments visible to the current actor."""
    actor = cast(User, request.user)
    search = request.GET.get("q", "")
    return render(
        request,
        "organizations/department_list.html",
        {
            "department_list": departments_visible_to(
                actor,
                search=search,
            ),
            "search": search,
        },
    )


@login_required
@permission_required("organizations.add_department", raise_exception=True)
@require_http_methods(["GET", "POST"])
def department_create(request: HttpRequest) -> HttpResponse:
    """Create a bilingual department."""
    actor = cast(User, request.user)
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_department(
            actor=actor,
            code=form.cleaned_data["code"],
            name_ar=form.cleaned_data["name_ar"],
            name_en=form.cleaned_data["name_en"],
            request=request,
        )
        messages.success(request, _("Department created successfully."))
        return redirect("organizations:list")
    return render(
        request,
        "organizations/department_form.html",
        {"form": form, "page_title": _("Create department")},
    )


@login_required
@permission_required("organizations.change_department", raise_exception=True)
@require_http_methods(["GET", "POST"])
def department_update(
    request: HttpRequest,
    department_id: int,
) -> HttpResponse:
    """Update department names while preserving its stable code."""
    actor = cast(User, request.user)
    department = get_object_or_404(Department, pk=department_id)
    form = DepartmentForm(
        request.POST or None,
        department=department,
        initial={
            "code": department.code,
            "name_ar": department.name_ar,
            "name_en": department.name_en,
        },
    )
    if request.method == "POST" and form.is_valid():
        update_department(
            actor=actor,
            department=department,
            name_ar=form.cleaned_data["name_ar"],
            name_en=form.cleaned_data["name_en"],
            request=request,
        )
        messages.success(request, _("Department updated successfully."))
        return redirect("organizations:list")
    return render(
        request,
        "organizations/department_form.html",
        {
            "department": department,
            "form": form,
            "page_title": _("Edit department"),
        },
    )


@login_required
@permission_required("organizations.archive_department", raise_exception=True)
@require_http_methods(["GET", "POST"])
def department_archive(
    request: HttpRequest,
    department_id: int,
) -> HttpResponse:
    """Confirm and archive a department without active members."""
    actor = cast(User, request.user)
    department = get_object_or_404(Department, pk=department_id)
    if request.method == "POST":
        try:
            archive_department(
                actor=actor,
                department=department,
                request=request,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Department archived successfully."))
        return redirect("organizations:list")
    return render(
        request,
        "organizations/department_confirm.html",
        {
            "department": department,
            "page_title": _("Archive department"),
            "confirmation_text": _(
                "A department can be archived only after all active users move "
                "or are deactivated."
            ),
            "submit_label": _("Archive"),
            "submit_class": "btn-danger",
        },
    )


@login_required
@permission_required("organizations.restore_department", raise_exception=True)
@require_http_methods(["GET", "POST"])
def department_restore(
    request: HttpRequest,
    department_id: int,
) -> HttpResponse:
    """Confirm and restore an archived department."""
    actor = cast(User, request.user)
    department = get_object_or_404(Department, pk=department_id)
    if request.method == "POST":
        restore_department(
            actor=actor,
            department=department,
            request=request,
        )
        messages.success(request, _("Department restored successfully."))
        return redirect("organizations:list")
    return render(
        request,
        "organizations/department_confirm.html",
        {
            "department": department,
            "page_title": _("Restore department"),
            "confirmation_text": _(
                "The department will become available for new account assignments."
            ),
            "submit_label": _("Restore"),
            "submit_class": "btn-success",
        },
    )
