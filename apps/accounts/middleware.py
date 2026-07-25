"""Account lifecycle middleware."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

ALLOWED_WHILE_PASSWORD_CHANGE_REQUIRED = {
    "accounts:login",
    "accounts:logout",
    "accounts:password_change",
    "admin:login",
    "admin:logout",
    "health",
    "set_language",
}


class ForcePasswordChangeMiddleware:
    """Keep temporary-password sessions inside the password-change workflow."""

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if user.is_authenticated and user.must_change_password:
            try:
                view_name = resolve(request.path_info).view_name
            except Resolver404:
                view_name = ""
            if (
                view_name not in ALLOWED_WHILE_PASSWORD_CHANGE_REQUIRED
                and not request.path_info.startswith("/static/")
            ):
                return redirect("accounts:password_change")
        return self.get_response(request)
