"""Foundation views with no business-domain behavior."""

import logging

from django.contrib.auth.decorators import login_required
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language

from apps.accounts.models import User
from apps.workspace.services import dashboard_context

logger = logging.getLogger(__name__)


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Render the actor-scoped Phase 12 dashboard."""
    actor = request.user
    assert isinstance(actor, User)
    return render(
        request,
        "workspace/dashboard.html",
        dashboard_context(actor, get_language() or "ar"),
    )


def health(request: HttpRequest) -> JsonResponse:
    """Report application and database health without implementation details."""
    del request
    health_connection = connections[DEFAULT_DB_ALIAS].copy(alias="health")
    try:
        # A fresh connection avoids waiting on a pooled socket after an outage.
        with health_connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.warning(
            "Database health check failed.",
            extra={"database": "unavailable", "event": "health_check"},
        )
        return JsonResponse(
            {"database": "unavailable", "status": "unhealthy"},
            status=503,
        )
    finally:
        health_connection.close()

    return JsonResponse({"database": "ok", "status": "ok"})
