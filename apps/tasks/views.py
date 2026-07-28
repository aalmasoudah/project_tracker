"""Thin Phase 5 views backed by services and selectors."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.progress.services import task_progress_for
from apps.tasks.forms import (
    AssignedTaskForm,
    TagForm,
    TaskCommentForm,
    TaskFileForm,
    TaskForm,
    TaskTagForm,
)
from apps.tasks.models import Tag, Task, TaskFile
from apps.tasks.selectors import (
    can_archive_task,
    can_manage_task,
    can_restore_task,
    can_update_assigned_task,
    task_history_visible_to,
    tasks_visible_to,
    visible_task_or_404,
    visible_task_relationships,
)
from apps.tasks.services import (
    add_task_comment,
    archive_task,
    create_task,
    replace_task_assignments,
    replace_task_tags,
    restore_task,
    save_tag,
    set_tag_archived,
    update_assigned_task,
    update_task,
    upload_task_file,
)

TASK_FIELDS = (
    "code",
    "project",
    "course",
    "parent",
    "name_ar",
    "name_en",
    "description",
    "status",
    "priority",
    "start_date",
    "due_date",
    "estimated_hours",
    "actual_hours",
    "blocking_reason",
)


@login_required
@permission_required("tasks.view_task", raise_exception=True)
def task_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    include_archived = request.GET.get("archived") == "1"
    page = Paginator(
        tasks_visible_to(
            actor,
            search=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            include_archived=include_archived,
        ),
        25,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "tasks/task_list.html",
        {
            "page": page,
            "search": request.GET.get("q", ""),
            "selected_status": request.GET.get("status", ""),
            "include_archived": include_archived,
            "status_choices": Task.Status.choices,
        },
    )


@login_required
def task_detail(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    manager = can_manage_task(actor, task)
    assigned_update = can_update_assigned_task(actor, task)
    visible_parent, visible_subtasks = visible_task_relationships(actor, task)
    return render(
        request,
        "tasks/task_detail.html",
        {
            "task": task,
            "progress": task_progress_for(actor, task),
            "visible_parent": visible_parent,
            "visible_subtasks": visible_subtasks,
            "assignments": task.assignments.filter(
                removed_at__isnull=True
            ).select_related("user"),
            "comments": task.comments.select_related("author"),
            "tag_links": task.tag_links.filter(removed_at__isnull=True).select_related(
                "tag"
            ),
            "files": task.files.select_related("uploaded_by"),
            "can_manage": manager,
            "can_assigned_update": assigned_update,
            "can_comment": actor.has_perm("tasks.comment_task")
            and not task.is_archived,
            "can_upload": actor.has_perm("tasks.upload_task_file")
            and not task.is_archived,
            "can_archive": (
                can_restore_task(actor, task)
                if task.is_archived
                else can_archive_task(actor, task)
            ),
            "can_history": actor.has_perm("tasks.view_task_history")
            and (
                actor.has_perm("tasks.view_all_tasks")
                or (task.project and task.project.manager_id == actor.pk)
                or (task.course and task.course.project.manager_id == actor.pk)
            ),
        },
    )


def _task_data(form: TaskForm) -> dict[str, object]:
    return {name: form.cleaned_data[name] for name in TASK_FIELDS}


@login_required
@permission_required("tasks.add_task", raise_exception=True)
@require_http_methods(["GET", "POST"])
def task_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    initial = {
        "status": "todo",
        "project": request.GET.get("project"),
        "course": request.GET.get("course"),
    }
    form = TaskForm(request.POST or None, actor=actor, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            task = create_task(
                actor=actor,
                assignees=form.cleaned_data["assignees"],
                primary_owner=form.cleaned_data["primary_owner"],
                request=request,
                **_task_data(form),
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Task created successfully."))
            return redirect("tasks:detail", task_id=task.pk)
    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "page_title": _("Create task")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def task_update(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    if not can_manage_task(actor, task):
        raise PermissionDenied
    form = TaskForm(request.POST or None, actor=actor, instance=task)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                task = update_task(
                    actor=actor, task=task, request=request, **_task_data(form)
                )
                replace_task_assignments(
                    actor=actor,
                    task=task,
                    assignees=form.cleaned_data["assignees"],
                    primary_owner=form.cleaned_data["primary_owner"],
                    request=request,
                )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Task updated successfully."))
            return redirect("tasks:detail", task_id=task.pk)
    return render(
        request,
        "tasks/task_form.html",
        {"form": form, "page_title": _("Edit task"), "task": task},
    )


@login_required
@require_http_methods(["GET", "POST"])
def assigned_task_update(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    if not can_update_assigned_task(actor, task):
        raise PermissionDenied
    form = AssignedTaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        try:
            update_assigned_task(
                actor=actor,
                task=task,
                status=form.cleaned_data["status"],
                actual_hours=form.cleaned_data["actual_hours"],
                blocking_reason=form.cleaned_data["blocking_reason"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Task updated successfully."))
            return redirect("tasks:detail", task_id=task.pk)
    return render(
        request,
        "tasks/assigned_form.html",
        {"form": form, "task": task},
    )


@login_required
@require_http_methods(["GET", "POST"])
def task_assignments(request: HttpRequest, task_id: int) -> HttpResponse:
    return task_update(request, task_id)


@login_required
@require_http_methods(["GET", "POST"])
def task_comment(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    form = TaskCommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            add_task_comment(
                actor=actor,
                task=task,
                body=form.cleaned_data["body"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Comment added successfully."))
            return redirect("tasks:detail", task_id=task.pk)
    return render(request, "tasks/comment_form.html", {"task": task, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def task_tags(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    if not can_manage_task(actor, task):
        raise PermissionDenied
    current = task.tag_links.filter(removed_at__isnull=True).values_list(
        "tag_id", flat=True
    )
    form = TaskTagForm(request.POST or None, initial={"tags": current})
    if request.method == "POST" and form.is_valid():
        replace_task_tags(
            actor=actor,
            task=task,
            tags=form.cleaned_data["tags"],
            request=request,
        )
        messages.success(request, _("Task tags updated successfully."))
        return redirect("tasks:detail", task_id=task.pk)
    return render(request, "tasks/tag_assign_form.html", {"task": task, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def task_file_upload(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    form = TaskFileForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            upload_task_file(
                actor=actor,
                task=task,
                upload=form.cleaned_data["file"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Task file uploaded successfully."))
            return redirect("tasks:detail", task_id=task.pk)
    return render(request, "tasks/file_form.html", {"task": task, "form": form})


@login_required
def task_file_download(request: HttpRequest, file_id: int) -> FileResponse:
    actor = cast(User, request.user)
    try:
        record = TaskFile.objects.select_related("task").get(pk=file_id)
    except TaskFile.DoesNotExist as error:
        raise Http404 from error
    visible_task_or_404(actor, record.task_id)
    if not actor.has_perm("tasks.view_taskfile"):
        raise Http404
    response = FileResponse(
        record.file.open("rb"),
        as_attachment=True,
        filename=record.original_name,
        content_type="application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _archive_view(
    request: HttpRequest, *, task_id: int, archived: bool
) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    permitted = (
        can_archive_task(actor, task) if archived else can_restore_task(actor, task)
    )
    if not permitted:
        raise PermissionDenied
    if request.method == "POST":
        try:
            if archived:
                archive_task(actor=actor, task=task, request=request)
            else:
                restore_task(actor=actor, task=task, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Task archive state updated."))
        return redirect("tasks:detail", task_id=task.pk)
    return render(
        request,
        "tasks/confirm.html",
        {
            "object": task,
            "page_title": _("Archive task") if archived else _("Restore task"),
            "submit_label": _("Archive") if archived else _("Restore"),
            "submit_class": "btn-danger" if archived else "btn-success",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def task_archive(request: HttpRequest, task_id: int) -> HttpResponse:
    return _archive_view(request, task_id=task_id, archived=True)


@login_required
@require_http_methods(["GET", "POST"])
def task_restore(request: HttpRequest, task_id: int) -> HttpResponse:
    return _archive_view(request, task_id=task_id, archived=False)


@login_required
def task_history(request: HttpRequest, task_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    task = visible_task_or_404(actor, task_id)
    return render(
        request,
        "tasks/history.html",
        {"task": task, "history": task_history_visible_to(actor, task)},
    )


@login_required
@permission_required("tasks.view_tag", raise_exception=True)
def tag_list(request: HttpRequest) -> HttpResponse:
    return render(request, "tasks/tag_list.html", {"tags": Tag.objects.all()})


def _tag_form(request: HttpRequest, *, tag: Tag | None, title: object) -> HttpResponse:
    actor = cast(User, request.user)
    form = TagForm(request.POST or None, instance=tag)
    if request.method == "POST" and form.is_valid():
        try:
            save_tag(
                actor=actor,
                instance=tag,
                code=form.cleaned_data["code"],
                name_ar=form.cleaned_data["name_ar"],
                name_en=form.cleaned_data["name_en"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Tag saved successfully."))
            return redirect("tasks:tag_list")
    return render(request, "tasks/tag_form.html", {"form": form, "page_title": title})


@login_required
@permission_required("tasks.add_tag", raise_exception=True)
@require_http_methods(["GET", "POST"])
def tag_create(request: HttpRequest) -> HttpResponse:
    return _tag_form(request, tag=None, title=_("Create tag"))


@login_required
@permission_required("tasks.change_tag", raise_exception=True)
@require_http_methods(["GET", "POST"])
def tag_update(request: HttpRequest, tag_id: int) -> HttpResponse:
    return _tag_form(
        request,
        tag=get_object_or_404(Tag, pk=tag_id, is_archived=False),
        title=_("Edit tag"),
    )


def _tag_archive(request: HttpRequest, *, tag_id: int, archived: bool) -> HttpResponse:
    actor = cast(User, request.user)
    tag = get_object_or_404(Tag, pk=tag_id)
    if request.method == "POST":
        try:
            set_tag_archived(actor=actor, tag=tag, archived=archived, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Tag archive state updated."))
        return redirect("tasks:tag_list")
    return render(
        request,
        "tasks/confirm.html",
        {
            "object": tag,
            "page_title": _("Archive tag") if archived else _("Restore tag"),
            "submit_label": _("Archive") if archived else _("Restore"),
            "submit_class": "btn-danger" if archived else "btn-success",
        },
    )


@login_required
@permission_required("tasks.archive_tag", raise_exception=True)
@require_http_methods(["GET", "POST"])
def tag_archive(request: HttpRequest, tag_id: int) -> HttpResponse:
    return _tag_archive(request, tag_id=tag_id, archived=True)


@login_required
@permission_required("tasks.restore_tag", raise_exception=True)
@require_http_methods(["GET", "POST"])
def tag_restore(request: HttpRequest, tag_id: int) -> HttpResponse:
    return _tag_archive(request, tag_id=tag_id, archived=False)
