"""Thin Phase 4 views backed by services and selectors."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.courses.forms import (
    CourseFileForm,
    CourseForm,
    CourseTrainerForm,
    TrainerForm,
)
from apps.courses.models import Course, CourseFile, Trainer
from apps.courses.selectors import (
    can_archive_course,
    can_manage_course,
    can_manage_course_trainers,
    can_upload_course_file,
    course_history_visible_to,
    courses_visible_to,
    trainers_visible_to,
    visible_course_or_404,
    visible_trainer_or_404,
)
from apps.courses.services import (
    archive_course,
    create_course,
    replace_course_trainers,
    restore_course,
    save_trainer,
    set_trainer_archived,
    update_course,
    upload_course_file,
)
from apps.progress.services import course_progress_for

COURSE_FIELDS = (
    "code",
    "project",
    "name_ar",
    "name_en",
    "description",
    "delivery_type",
    "location",
    "capacity",
    "start_at",
    "end_at",
    "status",
    "notes",
)
TRAINER_FIELDS = (
    "code",
    "name_ar",
    "name_en",
    "email",
    "phone",
    "organization",
    "notes",
)


@login_required
@permission_required("courses.view_course", raise_exception=True)
def course_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    include_archived = request.GET.get("archived") == "1"
    page = Paginator(
        courses_visible_to(
            actor,
            search=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            include_archived=include_archived,
        ),
        25,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "courses/course_list.html",
        {
            "page": page,
            "search": request.GET.get("q", ""),
            "selected_status": request.GET.get("status", ""),
            "include_archived": include_archived,
            "status_choices": Course.Status.choices,
        },
    )


@login_required
def course_detail(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    assignments = course.trainer_assignments.filter(
        removed_at__isnull=True
    ).select_related("trainer")
    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "assignments": assignments,
            "files": course.files.select_related("uploaded_by"),
            "show_contact": actor.has_perm("courses.view_trainer_contact"),
            "can_manage": can_manage_course(actor, course),
            "can_archive": can_archive_course(actor, course),
            "can_manage_trainers": can_manage_course_trainers(actor, course),
            "can_upload_file": can_upload_course_file(actor, course),
            "can_history": actor.has_perm("courses.view_course_history")
            and (
                actor.has_perm("courses.view_all_courses")
                or course.project.manager_id == actor.pk
            ),
            "progress": course_progress_for(actor, course),
        },
    )


def _course_form_data(form: CourseForm) -> dict[str, object]:
    return {name: form.cleaned_data[name] for name in COURSE_FIELDS}


@login_required
@permission_required("courses.add_course", raise_exception=True)
@require_http_methods(["GET", "POST"])
def course_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = CourseForm(request.POST or None, actor=actor, initial={"status": "draft"})
    if request.method == "POST" and form.is_valid():
        try:
            course = create_course(
                actor=actor, request=request, **_course_form_data(form)
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Course created successfully."))
            return redirect("courses:detail", course_id=course.pk)
    return render(
        request,
        "courses/course_form.html",
        {"form": form, "page_title": _("Create course")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def course_update(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    if not can_manage_course(actor, course):
        raise PermissionDenied
    form = CourseForm(request.POST or None, actor=actor, instance=course)
    if request.method == "POST" and form.is_valid():
        try:
            course = update_course(
                actor=actor,
                course=course,
                request=request,
                **_course_form_data(form),
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Course updated successfully."))
            return redirect("courses:detail", course_id=course.pk)
    return render(
        request,
        "courses/course_form.html",
        {"form": form, "page_title": _("Edit course"), "course": course},
    )


@login_required
@require_http_methods(["GET", "POST"])
def course_archive(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    if not can_archive_course(actor, course):
        raise PermissionDenied
    if request.method == "POST":
        archive_course(actor=actor, course=course, request=request)
        messages.success(request, _("Course archived successfully."))
        return redirect("courses:detail", course_id=course.pk)
    return render(
        request,
        "courses/confirm.html",
        {
            "object": course,
            "page_title": _("Archive course"),
            "message": _("Archiving makes the course read-only."),
            "submit_label": _("Archive"),
            "submit_class": "btn-danger",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def course_restore(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    if not can_archive_course(actor, course):
        raise PermissionDenied
    if request.method == "POST":
        try:
            restore_course(actor=actor, course=course, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Course restored successfully."))
        return redirect("courses:detail", course_id=course.pk)
    return render(
        request,
        "courses/confirm.html",
        {
            "object": course,
            "page_title": _("Restore course"),
            "message": _("The course will become editable again."),
            "submit_label": _("Restore"),
            "submit_class": "btn-success",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def course_trainers(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    if not can_manage_course_trainers(actor, course):
        raise PermissionDenied
    current = course.trainer_assignments.filter(removed_at__isnull=True).values_list(
        "trainer_id", flat=True
    )
    form = CourseTrainerForm(request.POST or None, initial={"trainers": current})
    if request.method == "POST" and form.is_valid():
        replace_course_trainers(
            actor=actor,
            course=course,
            trainers=form.cleaned_data["trainers"],
            request=request,
        )
        messages.success(request, _("Course trainers updated successfully."))
        return redirect("courses:detail", course_id=course.pk)
    return render(
        request, "courses/assignment_form.html", {"course": course, "form": form}
    )


@login_required
@require_http_methods(["GET", "POST"])
def course_file_upload(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    if not can_upload_course_file(actor, course):
        raise PermissionDenied
    form = CourseFileForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            upload_course_file(
                actor=actor,
                course=course,
                upload=form.cleaned_data["file"],
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Course file uploaded successfully."))
            return redirect("courses:detail", course_id=course.pk)
    return render(request, "courses/file_form.html", {"course": course, "form": form})


@login_required
def course_file_download(request: HttpRequest, file_id: int) -> FileResponse:
    actor = cast(User, request.user)
    try:
        record = CourseFile.objects.select_related("course").get(pk=file_id)
    except CourseFile.DoesNotExist as error:
        raise Http404 from error
    visible_course_or_404(actor, record.course_id)
    if not actor.has_perm("courses.view_coursefile"):
        raise Http404
    response = FileResponse(
        record.file.open("rb"),
        as_attachment=True,
        filename=record.original_name,
        content_type="application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def course_history(request: HttpRequest, course_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    course = visible_course_or_404(actor, course_id)
    return render(
        request,
        "courses/history.html",
        {"course": course, "history": course_history_visible_to(actor, course)},
    )


@login_required
@permission_required("courses.view_trainer", raise_exception=True)
def trainer_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    return render(
        request,
        "courses/trainer_list.html",
        {
            "trainers": trainers_visible_to(actor, search=request.GET.get("q", "")),
            "search": request.GET.get("q", ""),
            "show_contact": actor.has_perm("courses.view_trainer_contact"),
        },
    )


@login_required
def trainer_detail(request: HttpRequest, trainer_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    trainer = visible_trainer_or_404(actor, trainer_id)
    return render(
        request,
        "courses/trainer_detail.html",
        {
            "trainer": trainer,
            "show_contact": actor.has_perm("courses.view_trainer_contact"),
        },
    )


def _trainer_form(
    request: HttpRequest,
    *,
    trainer: Trainer | None,
    title: object,
) -> HttpResponse:
    actor = cast(User, request.user)
    form = TrainerForm(request.POST or None, instance=trainer)
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_trainer(
                actor=actor,
                instance=trainer,
                request=request,
                **{name: form.cleaned_data[name] for name in TRAINER_FIELDS},
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Trainer saved successfully."))
            return redirect("courses:trainer_detail", trainer_id=saved.pk)
    return render(
        request,
        "courses/trainer_form.html",
        {"form": form, "page_title": title, "trainer": trainer},
    )


@login_required
@permission_required("courses.add_trainer", raise_exception=True)
@require_http_methods(["GET", "POST"])
def trainer_create(request: HttpRequest) -> HttpResponse:
    return _trainer_form(request, trainer=None, title=_("Create trainer"))


@login_required
@permission_required("courses.change_trainer", raise_exception=True)
@require_http_methods(["GET", "POST"])
def trainer_update(request: HttpRequest, trainer_id: int) -> HttpResponse:
    trainer = visible_trainer_or_404(cast(User, request.user), trainer_id)
    if trainer.is_archived:
        raise PermissionDenied
    return _trainer_form(request, trainer=trainer, title=_("Edit trainer"))


def _trainer_archive(
    request: HttpRequest, *, trainer_id: int, archived: bool
) -> HttpResponse:
    actor = cast(User, request.user)
    trainer = visible_trainer_or_404(actor, trainer_id)
    if request.method == "POST":
        try:
            set_trainer_archived(
                actor=actor,
                trainer=trainer,
                archived=archived,
                request=request,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Trainer archive state updated."))
        return redirect("courses:trainer_detail", trainer_id=trainer.pk)
    return render(
        request,
        "courses/confirm.html",
        {
            "object": trainer,
            "page_title": _("Archive trainer") if archived else _("Restore trainer"),
            "message": _("Confirm the trainer archive change."),
            "submit_label": _("Archive") if archived else _("Restore"),
            "submit_class": "btn-danger" if archived else "btn-success",
        },
    )


@login_required
@permission_required("courses.archive_trainer", raise_exception=True)
@require_http_methods(["GET", "POST"])
def trainer_archive(request: HttpRequest, trainer_id: int) -> HttpResponse:
    return _trainer_archive(request, trainer_id=trainer_id, archived=True)


@login_required
@permission_required("courses.restore_trainer", raise_exception=True)
@require_http_methods(["GET", "POST"])
def trainer_restore(request: HttpRequest, trainer_id: int) -> HttpResponse:
    return _trainer_archive(request, trainer_id=trainer_id, archived=False)
