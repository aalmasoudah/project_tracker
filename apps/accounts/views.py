"""Thin account and authentication views backed by approved services."""

from typing import Any, Literal, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.i18n import set_language as django_set_language

from apps.accounts.forms import (
    AccountCreateForm,
    AccountUpdateForm,
    AdministrativePasswordResetForm,
    ProfileAvatarForm,
    ThrottledAuthenticationForm,
)
from apps.accounts.models import User, UserAvatar
from apps.accounts.roles import role_label
from apps.accounts.selectors import users_visible_to, visible_user_or_404
from apps.accounts.services import (
    complete_own_password_change,
    create_account,
    deactivate_account,
    deactivate_profile_avatar,
    managed_role_code,
    reactivate_account,
    reset_account_password,
    update_account,
    update_language_preference,
    update_profile_avatar,
)
from apps.audit import actions
from apps.audit.services import record_audit_event


class TrackerLoginView(LoginView):
    """Authenticate with throttling and restore the persisted language."""

    authentication_form = ThrottledAuthenticationForm
    redirect_authenticated_user = True
    template_name = "registration/login.html"

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        throttled_form = cast(ThrottledAuthenticationForm, form)
        response = super().form_valid(throttled_form)
        user = throttled_form.get_user()
        record_audit_event(
            actor=user,
            action=actions.LOGIN_SUCCEEDED,
            target_type="account",
            target_id=str(user.pk),
            target_label=user.display_name,
            request=self.request,
        )
        translation.activate(user.preferred_language)
        samesite = cast(
            Literal["Lax", "Strict", "None", False] | None,
            settings.LANGUAGE_COOKIE_SAMESITE,
        )
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            user.preferred_language,
            max_age=getattr(settings, "LANGUAGE_COOKIE_AGE", None),
            path=getattr(settings, "LANGUAGE_COOKIE_PATH", "/"),
            secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=samesite,
        )
        return response

    def get_success_url(self) -> str:
        user = self.request.user
        if user.is_authenticated and user.must_change_password:
            return reverse("accounts:password_change")
        return super().get_success_url()


class TrackerLogoutView(LogoutView):
    """Audit logout before Django flushes the session."""

    next_page = "/accounts/login/"

    def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        if request.user.is_authenticated:
            record_audit_event(
                actor=request.user,
                action=actions.LOGOUT,
                target_type="account",
                target_id=str(request.user.pk),
                target_label=request.user.display_name,
                request=request,
            )
        return super().post(request, *args, **kwargs)


@require_http_methods(["POST"])
def set_language_preference(request: HttpRequest) -> HttpResponse:
    """Use Django's safe redirect behavior and persist authenticated choices."""
    language_code = request.POST.get("language", "")
    supported_codes = {code for code, _label in settings.LANGUAGES}
    if request.user.is_authenticated and language_code in supported_codes:
        update_language_preference(
            user=request.user,
            language_code=language_code,
            request=request,
        )
    return django_set_language(request)


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request: HttpRequest) -> HttpResponse:
    """Change the current password and revoke every other session."""
    actor = cast(User, request.user)
    form = PasswordChangeForm(actor, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        complete_own_password_change(
            user=user,
            current_session_key=request.session.session_key,
            request=request,
        )
        messages.success(request, _("Your password was changed successfully."))
        return redirect("home")
    return render(
        request,
        "accounts/password_change.html",
        {"form": form},
    )


def _profile_context(actor: User, form: ProfileAvatarForm) -> dict[str, Any]:
    return {
        "profile_user": actor,
        "role_label": role_label(managed_role_code(actor)),
        "avatar_form": form,
        "active_avatar": actor.active_profile_avatar,
    }


@login_required
@require_http_methods(["GET"])
def profile(request: HttpRequest) -> HttpResponse:
    """Render the current user's own approved profile fields."""
    actor = cast(User, request.user)
    return render(
        request,
        "accounts/profile.html",
        _profile_context(actor, ProfileAvatarForm()),
    )


@login_required
@require_http_methods(["POST"])
def profile_avatar_update(request: HttpRequest) -> HttpResponse:
    """Validate and replace only the signed-in user's own avatar."""
    actor = cast(User, request.user)
    form = ProfileAvatarForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            update_profile_avatar(
                actor=actor,
                upload=form.cleaned_data["avatar"],
                request=request,
            )
        except ValidationError as error:
            form.add_error("avatar", error)
        else:
            messages.success(request, _("Your profile picture was updated."))
            return redirect("accounts:profile")
    return render(
        request,
        "accounts/profile.html",
        _profile_context(actor, form),
        status=400,
    )


@login_required
@require_http_methods(["POST"])
def profile_avatar_remove(request: HttpRequest) -> HttpResponse:
    """Deactivate only the signed-in user's displayed avatar."""
    actor = cast(User, request.user)
    removed = deactivate_profile_avatar(actor=actor, request=request)
    if removed:
        messages.success(request, _("Your profile picture was removed."))
    return redirect("accounts:profile")


@login_required
@require_http_methods(["GET"])
def profile_avatar_image(request: HttpRequest, user_id: int) -> FileResponse:
    """Stream one active private avatar after current account-scope checks."""
    actor = cast(User, request.user)
    if actor.pk != user_id:
        visible_user_or_404(actor, user_id)
    try:
        avatar = UserAvatar.objects.get(user_id=user_id, is_active=True)
        image = avatar.image.open("rb")
    except (UserAvatar.DoesNotExist, FileNotFoundError, OSError) as error:
        raise Http404 from error
    response = FileResponse(image, content_type="image/webp")
    response["Cache-Control"] = "private, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@login_required
def account_list(request: HttpRequest) -> HttpResponse:
    """Render the permission-scoped account directory."""
    actor = cast(User, request.user)
    search = request.GET.get("q", "")
    return render(
        request,
        "accounts/account_list.html",
        {
            "account_list": users_visible_to(actor, search=search),
            "search": search,
        },
    )


@login_required
def account_detail(request: HttpRequest, user_id: int) -> HttpResponse:
    """Render one visible account without object-existence leakage."""
    actor = cast(User, request.user)
    target = visible_user_or_404(actor, user_id)
    return render(
        request,
        "accounts/account_detail.html",
        {
            "profile_user": target,
            "role_label": role_label(managed_role_code(target)),
        },
    )


@login_required
@permission_required("accounts.manage_accounts", raise_exception=True)
@require_http_methods(["GET", "POST"])
def account_create(request: HttpRequest) -> HttpResponse:
    """Create an account through the transactional service."""
    actor = cast(User, request.user)
    form = AccountCreateForm(
        request.POST or None,
        actor=actor,
        initial={"preferred_language": User.Language.ARABIC},
    )
    if request.method == "POST" and form.is_valid():
        try:
            account = create_account(
                actor=actor,
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                display_name=form.cleaned_data["display_name"],
                department=form.cleaned_data["department"],
                role_code=form.cleaned_data["role"],
                preferred_language=form.cleaned_data["preferred_language"],
                temporary_password=form.cleaned_data["password1"],
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, _("Account created successfully."))
            return redirect("accounts:detail", user_id=account.pk)
    return render(
        request,
        "accounts/account_form.html",
        {"form": form, "page_title": _("Create account")},
    )


@login_required
@permission_required("accounts.manage_accounts", raise_exception=True)
@require_http_methods(["GET", "POST"])
def account_update(request: HttpRequest, user_id: int) -> HttpResponse:
    """Update an account while preserving its immutable username."""
    actor = cast(User, request.user)
    target = get_object_or_404(
        User.objects.select_related("department").prefetch_related("groups"),
        pk=user_id,
    )
    initial = {
        "email": target.email,
        "display_name": target.display_name,
        "department": target.department,
        "role": managed_role_code(target),
        "preferred_language": target.preferred_language,
    }
    form = AccountUpdateForm(
        request.POST or None,
        actor=actor,
        target=target,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_account(
                actor=actor,
                target=target,
                email=form.cleaned_data["email"],
                display_name=form.cleaned_data["display_name"],
                department=form.cleaned_data["department"],
                role_code=form.cleaned_data["role"],
                preferred_language=form.cleaned_data["preferred_language"],
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, _("Account updated successfully."))
            return redirect("accounts:detail", user_id=target.pk)
    return render(
        request,
        "accounts/account_form.html",
        {
            "form": form,
            "page_title": _("Edit account"),
            "profile_user": target,
        },
    )


@login_required
@permission_required("accounts.manage_accounts", raise_exception=True)
@require_http_methods(["GET", "POST"])
def account_deactivate(request: HttpRequest, user_id: int) -> HttpResponse:
    """Confirm and apply account deactivation."""
    actor = cast(User, request.user)
    target = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        try:
            deactivate_account(actor=actor, target=target, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Account deactivated successfully."))
        return redirect("accounts:detail", user_id=target.pk)
    return render(
        request,
        "accounts/account_confirm.html",
        {
            "profile_user": target,
            "page_title": _("Deactivate account"),
            "confirmation_text": _(
                "This immediately signs the user out and prevents future login."
            ),
            "submit_label": _("Deactivate"),
            "submit_class": "btn-danger",
        },
    )


@login_required
@permission_required("accounts.manage_accounts", raise_exception=True)
@require_http_methods(["GET", "POST"])
def account_reactivate(request: HttpRequest, user_id: int) -> HttpResponse:
    """Confirm and apply account reactivation."""
    actor = cast(User, request.user)
    target = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        try:
            reactivate_account(actor=actor, target=target, request=request)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, _("Account reactivated successfully."))
        return redirect("accounts:detail", user_id=target.pk)
    return render(
        request,
        "accounts/account_confirm.html",
        {
            "profile_user": target,
            "page_title": _("Reactivate account"),
            "confirmation_text": _("The user must sign in again after reactivation."),
            "submit_label": _("Reactivate"),
            "submit_class": "btn-success",
        },
    )


@login_required
@permission_required("accounts.manage_accounts", raise_exception=True)
@require_http_methods(["GET", "POST"])
def account_password_reset(request: HttpRequest, user_id: int) -> HttpResponse:
    """Set a temporary password and revoke the target's active sessions."""
    actor = cast(User, request.user)
    target = get_object_or_404(User, pk=user_id)
    form = AdministrativePasswordResetForm(target, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reset_account_password(
                actor=actor,
                target=target,
                temporary_password=form.cleaned_data["new_password1"],
                request=request,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(
                request,
                _("Temporary password set; the user must replace it at login."),
            )
            return redirect("accounts:detail", user_id=target.pk)
    return render(
        request,
        "accounts/password_reset.html",
        {"form": form, "profile_user": target},
    )
