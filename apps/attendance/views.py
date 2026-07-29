"""Internal scheduling/review and safe external capability views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.attendance.forms import (
    AttendanceForm,
    CorrectionForm,
    LinkIssueForm,
    RejectionForm,
    SessionForm,
)
from apps.attendance.models import (
    AttendanceEntry,
    AttendanceReview,
    AttendanceSubmission,
    SessionParticipant,
    TrainerLink,
)
from apps.attendance.selectors import (
    can_correct_submission,
    can_manage_session,
    can_review_submission,
    pending_submissions_for,
    resolve_token,
    sessions_visible_to,
    visible_session_or_404,
    visible_submission_or_404,
)
from apps.attendance.services import (
    archive_session,
    correct_attendance,
    create_sessions,
    issue_trainer_link,
    review_attendance,
    submit_attendance,
)


def _display_snapshot(
    snapshot: list[dict[str, object]],
    participant_names: dict[int, str],
) -> list[dict[str, object]]:
    labels = dict(AttendanceEntry.Value.choices)
    displayed: list[dict[str, object]] = []
    for item in snapshot:
        raw_participant_id = item.get("participant_id")
        participant_id = (
            raw_participant_id if isinstance(raw_participant_id, int) else 0
        )
        value = str(item.get("value", ""))
        displayed.append(
            {
                "participant_id": participant_id,
                "participant_name": participant_names.get(
                    participant_id, _("Unknown participant")
                ),
                "value": labels.get(value, value),
                "notes": item.get("notes", ""),
            }
        )
    return displayed


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
            "session_title": session.localized_title(get_language() or "ar"),
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
    submission = getattr(link, "submission", None)
    if link.session.is_archived or link.state == TrainerLink.State.REVOKED:
        response = render(request, "attendance/link_unavailable.html", status=410)
        return _secure_external_response(response)
    if link.state == TrainerLink.State.SUBMITTED:
        if submission is None:
            response = render(request, "attendance/link_unavailable.html", status=410)
        elif submission.state == AttendanceSubmission.State.APPROVED:
            response = render(
                request,
                "attendance/trainer_read_only.html",
                {
                    "submission": submission,
                    "entries": submission.entries.select_related(
                        "participant__enrollment__trainee"
                    ),
                    "session_title": link.session.localized_title(
                        get_language() or "ar"
                    ),
                },
            )
        else:
            response = render(request, "attendance/submitted.html")
        return _secure_external_response(response)
    if link.state != TrainerLink.State.ACTIVE or link.expires_at <= timezone.now():
        response = render(request, "attendance/link_unavailable.html", status=410)
        return _secure_external_response(response)
    participants = list(
        SessionParticipant.objects.filter(session=link.session).select_related(
            "enrollment__trainee"
        )
    )
    initial: dict[str, str] = {}
    rejection_reason = ""
    if (
        submission is not None
        and submission.state == AttendanceSubmission.State.REJECTED
    ):
        initial["trainer_notes"] = submission.trainer_notes
        for entry in submission.entries.all():
            initial[f"value_{entry.participant_id}"] = entry.value
            initial[f"notes_{entry.participant_id}"] = entry.notes
        latest_rejection = submission.reviews.filter(
            decision=AttendanceReview.Decision.REJECTED
        ).last()
        rejection_reason = latest_rejection.reason if latest_rejection else ""
    form = AttendanceForm(
        request.POST or None,
        request.FILES or None,
        participants=participants,
        initial=initial,
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
            "rejection_reason": rejection_reason,
            "session_title": link.session.localized_title(get_language() or "ar"),
        },
    )
    return _secure_external_response(response)


@login_required
@permission_required("attendance.review_attendance", raise_exception=True)
def review_queue(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    page = Paginator(pending_submissions_for(actor), 25).get_page(
        request.GET.get("page")
    )
    return render(request, "attendance/review_queue.html", {"page": page})


@login_required
def submission_detail(request: HttpRequest, submission_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    submission = visible_submission_or_404(actor, submission_id)
    entries = list(
        submission.entries.select_related("participant__enrollment__trainee")
    )
    participant_names = {
        entry.participant_id: entry.participant.enrollment.trainee.full_name
        for entry in entries
    }
    review_history = [
        (review, _display_snapshot(review.entry_snapshot, participant_names))
        for review in submission.reviews.all()
    ]
    correction_history = [
        (
            correction,
            _display_snapshot(correction.before_snapshot, participant_names),
            _display_snapshot(correction.after_snapshot, participant_names),
        )
        for correction in submission.corrections.all()
    ]
    return render(
        request,
        "attendance/review_detail.html",
        {
            "submission": submission,
            "entries": entries,
            "can_review": can_review_submission(actor, submission),
            "can_correct": can_correct_submission(actor, submission),
            "rejection_form": RejectionForm(),
            "review_history": review_history,
            "correction_history": correction_history,
            "session_title": submission.session.localized_title(get_language() or "ar"),
        },
    )


@login_required
@require_POST
def submission_approve(request: HttpRequest, submission_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    submission = visible_submission_or_404(actor, submission_id)
    review_attendance(
        actor=actor,
        submission=submission,
        decision=AttendanceReview.Decision.APPROVED,
        request=request,
    )
    messages.success(request, _("Attendance approved."))
    return redirect("attendance:submission-detail", submission_id=submission.pk)


@login_required
@require_POST
def submission_reject(request: HttpRequest, submission_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    submission = visible_submission_or_404(actor, submission_id)
    form = RejectionForm(request.POST)
    if not form.is_valid():
        entries = submission.entries.select_related("participant__enrollment__trainee")
        return render(
            request,
            "attendance/review_detail.html",
            {
                "submission": submission,
                "entries": entries,
                "can_review": can_review_submission(actor, submission),
                "can_correct": can_correct_submission(actor, submission),
                "rejection_form": form,
                "session_title": submission.session.localized_title(
                    get_language() or "ar"
                ),
            },
            status=400,
        )
    review_attendance(
        actor=actor,
        submission=submission,
        decision=AttendanceReview.Decision.REJECTED,
        reason=form.cleaned_data["reason"],
        request=request,
    )
    messages.success(request, _("Attendance rejected and the trainer link reopened."))
    return redirect("attendance:submission-detail", submission_id=submission.pk)


@login_required
@require_http_methods(["GET", "POST"])
def submission_correct(request: HttpRequest, submission_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    submission = visible_submission_or_404(actor, submission_id)
    if not can_correct_submission(actor, submission):
        raise PermissionDenied
    participants = list(
        SessionParticipant.objects.filter(session=submission.session).select_related(
            "enrollment__trainee"
        )
    )
    form = CorrectionForm(
        request.POST or None,
        submission=submission,
        participants=participants,
    )
    rows = [
        (
            participant,
            form[f"value_{participant.pk}"],
            form[f"notes_{participant.pk}"],
        )
        for participant in participants
    ]
    if request.method == "POST" and form.is_valid():
        try:
            correct_attendance(
                actor=actor,
                submission=submission,
                entries=form.entry_values(),
                reason=form.cleaned_data["reason"],
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Attendance corrected without reapproval."))
            return redirect("attendance:submission-detail", submission_id=submission.pk)
    return render(
        request,
        "attendance/correction_form.html",
        {
            "submission": submission,
            "attendance_rows": rows,
            "form": form,
            "session_title": submission.session.localized_title(get_language() or "ar"),
        },
    )


def _secure_external_response(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "same-origin"
    response["X-Frame-Options"] = "DENY"
    response["X-Content-Type-Options"] = "nosniff"
    return response
