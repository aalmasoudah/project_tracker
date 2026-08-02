"""Owner-scoped notification, preference, and delivery-status views."""

from typing import cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.notifications.forms import NotificationPreferencesForm
from apps.notifications.selectors import (
    delivery_attempts_for,
    notifications_for,
    visible_notification_or_404,
)
from apps.notifications.services import (
    mark_all_notifications_read,
    mark_notification_read,
    update_preferences,
)


@login_required
def notification_list(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    queryset = notifications_for(actor)
    if request.GET.get("unread") == "1":
        queryset = queryset.filter(is_read=False)
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "notifications/notification_list.html",
        {"page": page, "unread_only": request.GET.get("unread") == "1"},
    )


@login_required
@require_POST
def notification_open(request: HttpRequest, notification_id: int) -> HttpResponse:
    actor = cast(User, request.user)
    notification = visible_notification_or_404(actor, notification_id)
    notification = mark_notification_read(actor=actor, notification=notification)
    return redirect(notification.target_path or "notifications:list")


@login_required
@require_POST
def mark_all_read(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    count = mark_all_notifications_read(actor=actor)
    messages.success(
        request,
        ngettext(
            "Marked %(count)s notification as read.",
            "Marked %(count)s notifications as read.",
            count,
        )
        % {"count": count},
    )
    return redirect("notifications:list")


@login_required
@require_http_methods(["GET", "POST"])
def preferences(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    form = NotificationPreferencesForm(
        request.POST or None,
        recipient=actor,
    )
    if request.method == "POST" and form.is_valid():
        update_preferences(
            actor=actor,
            values=form.preference_values(),
            request=request,
        )
        messages.success(request, _("Notification preferences saved."))
        return redirect("notifications:preferences")
    return render(
        request,
        "notifications/preferences.html",
        {"form": form},
    )


@login_required
@permission_required("notifications.view_delivery_status", raise_exception=True)
def delivery_status(request: HttpRequest) -> HttpResponse:
    actor = cast(User, request.user)
    page = Paginator(delivery_attempts_for(actor), 50).get_page(request.GET.get("page"))
    return render(request, "notifications/delivery_status.html", {"page": page})
