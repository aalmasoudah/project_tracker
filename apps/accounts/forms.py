"""Localized account, authentication, and lifecycle forms."""

from typing import Any, cast

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.accounts.authentication import (
    check_login_locked,
    clear_login_failures,
    record_login_failure,
    throttle_keys,
)
from apps.accounts.models import User
from apps.accounts.normalization import normalize_email, normalize_username
from apps.accounts.roles import (
    NON_TECHNICAL_ROLE_CODES,
    ROLE_DEFINITIONS,
    ROLE_LABELS,
    TECHNICAL_ADMIN,
)
from apps.audit import actions
from apps.audit.services import record_audit_event
from apps.organizations.models import Department


def _style_form_fields(form: forms.BaseForm) -> None:
    """Apply the local Bootstrap form treatment consistently."""
    for field in form.fields.values():
        if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
            field.widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        else:
            field.widget.attrs.setdefault("class", "form-control")


class ThrottledAuthenticationForm(AuthenticationForm):
    """Use generic errors and the approved account/IP login throttles."""

    # Django's form class configuration is intentionally copied per instance.
    error_messages: dict[str, Any] = {  # noqa: RUF012
        "invalid_login": _(
            "Unable to sign in with the provided credentials. Try again later "
            "or contact an administrator."
        ),
        "inactive": _(
            "Unable to sign in with the provided credentials. Try again later "
            "or contact an administrator."
        ),
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _style_form_fields(self)
        self.fields["username"].label = _("Username")
        self.fields["password"].label = _("Password")

    def clean(self) -> dict[str, Any]:
        """Authenticate only after checking and updating both throttle scopes."""
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password or self.request is None:
            return self.cleaned_data

        keys = throttle_keys(self.request, username)
        lock_state = check_login_locked(keys)
        if lock_state.locked:
            record_audit_event(
                action=actions.LOGIN_LOCKED,
                target_type="authentication",
                metadata={
                    "account_hash": keys.account,
                    "account_locked": lock_state.account_locked,
                    "ip_locked": lock_state.ip_locked,
                },
                request=self.request,
            )
            raise self.get_invalid_login_error()

        self.user_cache = authenticate(
            self.request,
            username=username,
            password=password,
        )
        if self.user_cache is None:
            lock_state = record_login_failure(keys)
            record_audit_event(
                action=(
                    actions.LOGIN_LOCKED if lock_state.locked else actions.LOGIN_FAILED
                ),
                target_type="authentication",
                metadata={
                    "account_hash": keys.account,
                    "account_locked": lock_state.account_locked,
                    "ip_locked": lock_state.ip_locked,
                },
                request=self.request,
            )
            raise self.get_invalid_login_error()

        self.confirm_login_allowed(self.user_cache)
        clear_login_failures(keys)
        return self.cleaned_data


class AccountFormBase(forms.Form):
    """Shared validation for Technical Admin account forms."""

    email = forms.EmailField(label=_("Email address"))
    display_name = forms.CharField(label=_("Display name"), max_length=150)
    department = forms.ModelChoiceField(
        label=_("Department"),
        queryset=Department.objects.none(),
        required=False,
    )
    role = forms.ChoiceField(label=_("Role"))
    preferred_language = forms.ChoiceField(
        label=_("Preferred language"),
        choices=User.Language.choices,
    )

    def __init__(
        self,
        *args: Any,
        actor: User,
        target: User | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.target = target
        department_field = cast(
            "forms.ModelChoiceField[Department]",
            self.fields["department"],
        )
        department_field.queryset = Department.objects.filter(
            is_archived=False
        ).order_by("code")
        role_field = cast(forms.ChoiceField, self.fields["role"])

        allowed_roles = list(ROLE_DEFINITIONS)
        if not actor.is_superuser:
            allowed_roles = [
                role for role in allowed_roles if role.code != TECHNICAL_ADMIN
            ]
        current_role = (
            target.groups.filter(name__in=ROLE_LABELS)
            .values_list("name", flat=True)
            .first()
            if target is not None
            else None
        )
        if (
            target is not None
            and current_role == TECHNICAL_ADMIN
            and not actor.is_superuser
        ):
            role_field.choices = [(TECHNICAL_ADMIN, ROLE_LABELS[TECHNICAL_ADMIN])]
            role_field.disabled = True
        else:
            role_field.choices = [(role.code, role.label) for role in allowed_roles]
        _style_form_fields(self)

    def clean_email(self) -> str:
        email = normalize_email(cast(str, self.cleaned_data["email"]))
        queryset = User.objects.filter(email__iexact=email)
        if self.target is not None:
            queryset = queryset.exclude(pk=self.target.pk)
        if queryset.exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

    def clean_display_name(self) -> str:
        display_name = cast(str, self.cleaned_data["display_name"]).strip()
        if not display_name:
            raise ValidationError(_("Display name is required."))
        return display_name

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        role_code = cleaned_data.get("role")
        department = cleaned_data.get("department")
        if role_code in NON_TECHNICAL_ROLE_CODES and department is None:
            self.add_error(
                "department",
                _("A department is required for this role."),
            )
        if department is not None and department.is_archived:
            self.add_error(
                "department",
                _("Archived departments cannot receive users."),
            )
        return cleaned_data


class AccountCreateForm(AccountFormBase):
    """Create an internal account with one temporary password."""

    username = forms.CharField(
        label=_("Username"),
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )
    password1 = forms.CharField(
        label=_("Temporary password"),
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("Confirm temporary password"),
        strip=False,
        widget=forms.PasswordInput,
    )

    field_order = (
        "username",
        "display_name",
        "email",
        "department",
        "role",
        "preferred_language",
        "password1",
        "password2",
    )

    def clean_username(self) -> str:
        username = normalize_username(cast(str, self.cleaned_data["username"]))
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_("A user with that username already exists."))
        return username

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("The two password fields did not match."))
        if password1:
            candidate = User(
                username=cleaned_data.get("username", ""),
                email=cleaned_data.get("email", ""),
                display_name=cleaned_data.get("display_name", ""),
            )
            try:
                password_validation.validate_password(password1, candidate)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data


class AccountUpdateForm(AccountFormBase):
    """Edit approved account fields while keeping username immutable."""


# django-stubs models this as generic, but Django's runtime class is not subscriptable.
class AdministrativePasswordResetForm(SetPasswordForm):  # type: ignore[type-arg]
    """Set a temporary password using Django's configured validators."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = _("Temporary password")
        self.fields["new_password2"].label = _("Confirm temporary password")
        _style_form_fields(self)


class PreferredLanguageForm(forms.Form):
    """Persist one approved interface language."""

    language = forms.ChoiceField(
        label=_("Preferred language"),
        choices=User.Language.choices,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _style_form_fields(self)


class ProfileAvatarForm(forms.Form):
    """Accept one bounded image; decoded verification happens in the service."""

    avatar = forms.FileField(
        label=_("Profile picture"),
        help_text=_("JPEG, PNG, or WebP. Maximum size 5 MB."),
        widget=forms.ClearableFileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "form-control",
            }
        ),
    )

    def clean_avatar(self) -> Any:
        avatar = self.cleaned_data["avatar"]
        if avatar.size > 5 * 1024 * 1024:
            raise ValidationError(_("The profile picture must not exceed 5 MB."))
        return avatar
