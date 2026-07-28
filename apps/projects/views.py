"""Thin Phase 3 project views backed by services and selectors."""

from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.progress.services import project_progress_for
from apps.projects.forms import ProjectForm, ReferenceForm, TeamForm
from apps.projects.models import Category, Client, Project
from apps.projects.selectors import (
    can_archive_project,
    can_manage_project,
    can_view_project_budget,
    project_history_visible_to,
    projects_visible_to,
    visible_project_or_404,
)
from apps.projects.services import (
    archive_project,
    create_project,
    replace_project_team,
    restore_project,
    save_reference,
    set_reference_archived,
    update_project,
)

PROJECT_FORM_FIELDS = (
    "code",
    "name_ar",
    "name_en",
    "department",
    "client",
    "category",
    "manager",
    "supervisor",
    "status",
    "priority",
    "start_date",
    "end_date",
    "budget",
    "goals",
    "requirements",
    "notes",
)


def _project_form_data(form: ProjectForm) -> dict[str, object]:
    return {field: form.cleaned_data[field] for field in PROJECT_FORM_FIELDS}


@login_required
@permission_required("projects.view_project", raise_exception=True)
def project_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    include_archived = request.GET.get("archived") == "1"
    queryset = projects_visible_to(
        actor,
        search=request.GET.get("q", ""),
        status=request.GET.get("status", ""),
        priority=request.GET.get("priority", ""),
        include_archived=include_archived,
    )
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "projects/project_list.html",
        {
            "page": page,
            "search": request.GET.get("q", ""),
            "selected_status": request.GET.get("status", ""),
            "selected_priority": request.GET.get("priority", ""),
            "include_archived": include_archived,
            "status_choices": Project.Status.choices,
            "priority_choices": Project.Priority.choices,
        },
    )


@login_required
def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "show_budget": can_view_project_budget(actor, project),
            "can_manage": can_manage_project(actor, project),
            "can_archive": can_archive_project(actor, project),
            "can_history": actor.has_perm("projects.view_project_history")
            and (
                actor.has_perm("projects.view_all_projects")
                or project.manager_id == actor.pk
            ),
            "memberships": project.memberships.filter(
                removed_at__isnull=True
            ).select_related("user"),
            "progress": project_progress_for(actor, project),
        },
    )


@login_required
@permission_required("projects.add_project", raise_exception=True)
@require_http_methods(["GET", "POST"])
def project_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = ProjectForm(
        request.POST or None,
        actor=actor,
        initial={
            "department": actor.department_id,
            "manager": actor.pk,
            "status": Project.Status.DRAFT,
            "priority": Project.Priority.MEDIUM,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            project = create_project(
                actor=actor,
                request=request,
                **_project_form_data(form),
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Project created successfully."))
            return redirect("projects:detail", project_id=project.pk)
    return render(
        request,
        "projects/project_form.html",
        {"form": form, "page_title": _("Create project")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def project_update(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not can_manage_project(actor, project):
        raise PermissionDenied
    form = ProjectForm(
        request.POST or None,
        instance=project,
        actor=actor,
    )
    if request.method == "POST" and form.is_valid():
        try:
            project = update_project(
                actor=actor,
                project=project,
                request=request,
                **_project_form_data(form),
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Project updated successfully."))
            return redirect("projects:detail", project_id=project.pk)
    return render(
        request,
        "projects/project_form.html",
        {"form": form, "page_title": _("Edit project"), "project": project},
    )


@login_required
@require_http_methods(["GET", "POST"])
def project_archive(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not can_archive_project(actor, project):
        raise PermissionDenied
    if request.method == "POST":
        try:
            archive_project(actor=actor, project=project, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Project archived successfully."))
        return redirect("projects:detail", project_id=project.pk)
    return render(
        request,
        "projects/project_confirm.html",
        {
            "project": project,
            "page_title": _("Archive project"),
            "confirmation_text": _("Archived projects become read-only."),
            "submit_label": _("Archive"),
            "submit_class": "btn-danger",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def project_restore(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not can_archive_project(actor, project):
        raise PermissionDenied
    if request.method == "POST":
        try:
            restore_project(actor=actor, project=project, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Project restored successfully."))
        return redirect("projects:detail", project_id=project.pk)
    return render(
        request,
        "projects/project_confirm.html",
        {
            "project": project,
            "page_title": _("Restore project"),
            "confirmation_text": _("The project will become editable again."),
            "submit_label": _("Restore"),
            "submit_class": "btn-success",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def project_team(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not (
        actor.has_perm("projects.manage_project_team")
        and can_manage_project(actor, project)
    ):
        raise PermissionDenied
    initial_members = project.memberships.filter(removed_at__isnull=True).values_list(
        "user_id", flat=True
    )
    form = TeamForm(
        request.POST or None,
        project=project,
        initial={"members": initial_members},
    )
    if request.method == "POST" and form.is_valid():
        try:
            replace_project_team(
                actor=actor,
                project=project,
                members=form.cleaned_data["members"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Project team updated successfully."))
            return redirect("projects:detail", project_id=project.pk)
    return render(
        request,
        "projects/team_form.html",
        {"form": form, "project": project},
    )


@login_required
def project_history(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    history = project_history_visible_to(actor, project)
    return render(
        request,
        "projects/project_history.html",
        {"project": project, "history": history},
    )


def _reference_list(
    request: HttpRequest,
    *,
    model: type[Client] | type[Category],
    title: Any,
    create_url: str,
) -> HttpResponse:
    records = model.objects.all().order_by("code")
    return render(
        request,
        "projects/reference_list.html",
        {
            "records": records,
            "page_title": title,
            "create_url": create_url,
            "model_name": model._meta.model_name,
        },
    )


def _reference_form(
    request: HttpRequest,
    *,
    model: type[Client] | type[Category],
    instance: Client | Category | None,
    page_title: Any,
    list_url: str,
) -> HttpResponse:
    actor = cast(User, request.user)
    if instance is not None and instance.is_archived:
        raise PermissionDenied(_("Archived reference records are read-only."))
    form = ReferenceForm(
        request.POST or None,
        instance=instance,
        model_class=model,
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_reference(
                actor=actor,
                model=model,
                code=form.cleaned_data["code"],
                name_ar=form.cleaned_data["name_ar"],
                name_en=form.cleaned_data["name_en"],
                instance=instance,
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Reference record saved successfully."))
            return redirect(list_url)
    return render(
        request,
        "projects/reference_form.html",
        {"form": form, "page_title": page_title, "list_url": list_url},
    )


def _reference_archive(
    request: HttpRequest,
    *,
    model: type[Client] | type[Category],
    record_id: int,
    archived: bool,
    list_url: str,
) -> HttpResponse:
    actor = cast(User, request.user)
    record = cast(Client | Category, get_object_or_404(model, pk=record_id))
    if request.method == "POST":
        try:
            set_reference_archived(
                actor=actor,
                reference=record,
                archived=archived,
                request=request,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Reference archive state updated."))
        return redirect(list_url)
    return render(
        request,
        "projects/reference_confirm.html",
        {
            "record": record,
            "page_title": _("Archive") if archived else _("Restore"),
            "submit_label": _("Archive") if archived else _("Restore"),
            "submit_class": "btn-danger" if archived else "btn-success",
            "list_url": list_url,
        },
    )


@login_required
@permission_required("projects.view_client", raise_exception=True)
def client_list(request: HttpRequest) -> HttpResponse:
    return _reference_list(
        request,
        model=Client,
        title=_("Clients"),
        create_url="projects:client_create",
    )


@login_required
@permission_required("projects.add_client", raise_exception=True)
@require_http_methods(["GET", "POST"])
def client_create(request: HttpRequest) -> HttpResponse:
    return _reference_form(
        request,
        model=Client,
        instance=None,
        page_title=_("Create client"),
        list_url="projects:client_list",
    )


@login_required
@permission_required("projects.change_client", raise_exception=True)
@require_http_methods(["GET", "POST"])
def client_update(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_form(
        request,
        model=Client,
        instance=get_object_or_404(Client, pk=record_id),
        page_title=_("Edit client"),
        list_url="projects:client_list",
    )


@login_required
@permission_required("projects.archive_client", raise_exception=True)
@require_http_methods(["GET", "POST"])
def client_archive(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_archive(
        request,
        model=Client,
        record_id=record_id,
        archived=True,
        list_url="projects:client_list",
    )


@login_required
@permission_required("projects.restore_client", raise_exception=True)
@require_http_methods(["GET", "POST"])
def client_restore(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_archive(
        request,
        model=Client,
        record_id=record_id,
        archived=False,
        list_url="projects:client_list",
    )


@login_required
@permission_required("projects.view_category", raise_exception=True)
def category_list(request: HttpRequest) -> HttpResponse:
    return _reference_list(
        request,
        model=Category,
        title=_("Categories"),
        create_url="projects:category_create",
    )


@login_required
@permission_required("projects.add_category", raise_exception=True)
@require_http_methods(["GET", "POST"])
def category_create(request: HttpRequest) -> HttpResponse:
    return _reference_form(
        request,
        model=Category,
        instance=None,
        page_title=_("Create category"),
        list_url="projects:category_list",
    )


@login_required
@permission_required("projects.change_category", raise_exception=True)
@require_http_methods(["GET", "POST"])
def category_update(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_form(
        request,
        model=Category,
        instance=get_object_or_404(Category, pk=record_id),
        page_title=_("Edit category"),
        list_url="projects:category_list",
    )


@login_required
@permission_required("projects.archive_category", raise_exception=True)
@require_http_methods(["GET", "POST"])
def category_archive(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_archive(
        request,
        model=Category,
        record_id=record_id,
        archived=True,
        list_url="projects:category_list",
    )


@login_required
@permission_required("projects.restore_category", raise_exception=True)
@require_http_methods(["GET", "POST"])
def category_restore(request: HttpRequest, record_id: int) -> HttpResponse:
    return _reference_archive(
        request,
        model=Category,
        record_id=record_id,
        archived=False,
        list_url="projects:category_list",
    )
