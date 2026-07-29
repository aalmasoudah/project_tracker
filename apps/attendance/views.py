"""Internal scheduling and safe external capability views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.attendance.forms import AttendanceForm, LinkIssueForm, SessionForm
from apps.attendance.models import SessionParticipant, TrainerLink
from apps.attendance.selectors import (
    can_manage_session,
    resolve_token,
    sessions_visible_to,
    visible_session_or_404,
)
from apps.attendance.services import (
    archive_session,
    create_sessions,
    issue_trainer_link,
    submit_attendance,
)


@login_required
@permission_required("attendance.view_session", raise_exception=True)
def session_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    page = Paginator(
        sessions_visible_to(actor, include_archived=request.GET.get("archived") == "1"),
        25,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "attendance/session_list.html",
        {"page": page, "include_archived": request.GET.get("archived") == "1"},
    )


@login_required
def session_detail(request: HttpRequest, session_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    session = visible_session_or_404(actor, session_id)
    participants = session.participants.select_related("enrollment__trainee")
    return render(
        request,
        "attendance/session_detail.html",
        {
            "session": session,
            "participants": participants,
            "can_manage": can_manage_session(actor, session),
            "issue_form": LinkIssueForm(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def session_create(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    if not can_manage_session(actor):
        raise PermissionDenied
    form = SessionForm(request.POST or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            sessions = create_sessions(
                actor=actor, request=request, **form.cleaned_data
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(
                request,
                _("Created %(count)s session(s).") % {"count": len(sessions)},
            )
            return redirect("attendance:detail", session_id=sessions[0].pk)
    return render(request, "attendance/session_form.html", {"form": form})


@login_required
@require_POST
def session_archive(request: HttpRequest, session_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    session = visible_session_or_404(actor, session_id)
    archive_session(actor=actor, session=session, request=request)
    messages.success(request, _("Session archived."))
    return redirect("attendance:detail", session_id=session.pk)


@login_required
@require_POST
def link_issue(request: HttpRequest, session_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    session = visible_session_or_404(actor, session_id)
    form = LinkIssueForm(request.POST)
    if not form.is_valid():
        raise ValidationError(form.errors.as_text())
    link, token = issue_trainer_link(
        actor=actor,
        session=session,
        lifetime_hours=form.cleaned_data["lifetime_hours"],
        request=request,
    )
    url = request.build_absolute_uri(
        reverse("attendance:trainer", kwargs={"token": token})
    )
    response = render(
        request,
        "attendance/link_issued.html",
        {"session": session, "link": link, "trainer_url": url},
    )
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "same-origin"
    return response


@require_http_methods(["GET", "POST"])
def trainer_attendance(request: HttpRequest, token: str) -> HttpResponse:
    link = resolve_token(token)
    if link is None:
        response = render(request, "attendance/link_unavailable.html", status=410)
        return _secure_external_response(response)
    invalid = (
        link.state != TrainerLink.State.ACTIVE
        or link.expires_at <= timezone.now()
        or link.session.is_archived
    )
    if invalid:
        response = render(request, "attendance/link_unavailable.html", status=410)
        return _secure_external_response(response)
    participants = list(
        SessionParticipant.objects.filter(session=link.session).select_related(
            "enrollment__trainee"
        )
    )
    form = AttendanceForm(
        request.POST or None,
        request.FILES or None,
        participants=participants,
    )
    attendance_rows = [
        (
            participant,
            form[f"value_{participant.pk}"],
            form[f"notes_{participant.pk}"],
        )
        for participant in participants
    ]
    if request.method == "POST" and form.is_valid():
        try:
            submit_attendance(
                link=link,
                entries=form.entry_values(),
                trainer_notes=form.cleaned_data["trainer_notes"],
                evidence_files=form.cleaned_data["evidence"],
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, str(error))
        else:
            response = render(request, "attendance/submitted.html")
            return _secure_external_response(response)
    response = render(
        request,
        "attendance/trainer_form.html",
        {
            "link": link,
            "session": link.session,
            "attendance_rows": attendance_rows,
            "form": form,
        },
    )
    return _secure_external_response(response)


def _secure_external_response(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "same-origin"
    response["X-Frame-Options"] = "DENY"
    response["X-Content-Type-Options"] = "nosniff"
    return response
