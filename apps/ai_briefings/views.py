"""Thin bilingual AI briefing views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.models import User
from apps.ai_briefings.forms import BriefingRequestForm
from apps.ai_briefings.models import AIBriefing
from apps.ai_briefings.policies import can_generate_briefing, can_review_briefing
from apps.ai_briefings.selectors import source_url_for, visible_briefing_or_404
from apps.ai_briefings.services import request_briefing, review_briefing
from apps.projects.selectors import visible_project_or_404


def _status_context(actor: User, briefing: AIBriefing) -> dict[str, object]:
    sources = {source.source_ref: source for source in briefing.sources.all()}

    def cited_items(section: object) -> list[dict[str, object]]:
        if not isinstance(section, list):
            return []
        presented: list[dict[str, object]] = []
        for raw_item in section:
            if not isinstance(raw_item, dict):
                continue
            citation_links = []
            raw_citations = raw_item.get("citations", [])
            if isinstance(raw_citations, list):
                for citation in raw_citations:
                    source = sources.get(str(citation))
                    if source is not None:
                        citation_links.append(
                            {
                                "ref": source.source_ref,
                                "label": source.source_label,
                                "url": source_url_for(actor, source),
                            }
                        )
            presented.append(
                {
                    "text": str(raw_item.get("text", "")),
                    "severity": str(raw_item.get("severity", "")),
                    "citations": citation_links,
                }
            )
        return presented

    output = briefing.output_data if isinstance(briefing.output_data, dict) else {}
    return {
        "briefing": briefing,
        "summary": str(output.get("summary", "")),
        "highlights": cited_items(output.get("highlights")),
        "risks": cited_items(output.get("risks")),
        "upcoming": cited_items(output.get("upcoming")),
        "recommended_actions": cited_items(output.get("recommended_actions")),
        "data_gaps": (
            output.get("data_gaps", [])
            if isinstance(output.get("data_gaps", []), list)
            else []
        ),
        "can_review": can_review_briefing(actor, briefing),
    }


@login_required
@require_http_methods(["GET", "POST"])
def briefing_request(request: HttpRequest, project_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    project = visible_project_or_404(actor, project_id)
    if not can_generate_briefing(actor, project):
        raise PermissionDenied
    form = BriefingRequestForm(request.POST or None, actor=actor)
    if request.method == "POST" and form.is_valid():
        try:
            briefing = request_briefing(
                actor=actor,
                project=project,
                language=cast(str, form.cleaned_data["language"]),
                detail_level=cast(str, form.cleaned_data["detail_level"]),
                evidence_window_days=cast(
                    int, form.cleaned_data["evidence_window_days"]
                ),
                request=request,
            )
        except (PermissionDenied, ValidationError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("AI briefing request queued."))
            return redirect("ai_briefings:detail", briefing_id=briefing.pk)
    return render(
        request,
        "ai_briefings/request.html",
        {"project": project, "form": form},
    )


@login_required
@require_GET
def briefing_detail(request: HttpRequest, briefing_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    briefing = visible_briefing_or_404(actor, briefing_id)
    return render(
        request,
        "ai_briefings/detail.html",
        _status_context(actor, briefing),
    )


@login_required
@require_GET
def briefing_status(request: HttpRequest, briefing_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    briefing = visible_briefing_or_404(actor, briefing_id)
    return render(
        request,
        "ai_briefings/_status.html",
        _status_context(actor, briefing),
    )


@login_required
@require_POST
def briefing_review(request: HttpRequest, briefing_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    briefing = visible_briefing_or_404(actor, briefing_id)
    review_briefing(actor=actor, briefing=briefing, request=request)
    messages.success(request, _("AI briefing marked as reviewed."))
    return redirect("ai_briefings:detail", briefing_id=briefing.pk)
