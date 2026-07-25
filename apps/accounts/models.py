"""Authentication models created before all later business domains."""

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import (
    normalize_account_search,
    normalize_email,
    normalize_username,
)


class User(AbstractUser):
    """Approved internal user identity and account lifecycle."""

    class Language(models.TextChoices):
        ARABIC = "ar", _("Arabic")
        ENGLISH = "en", _("English")

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        validators=[AbstractUser.username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )
    email = models.EmailField(_("email address"))
    display_name = models.CharField(
        _("display name"),
        max_length=150,
        validators=[MinLengthValidator(1)],
    )
    search_key = models.CharField(
        max_length=500,
        editable=False,
        db_index=True,
    )
    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.PROTECT,
        related_name="users",
        blank=True,
        null=True,
        verbose_name=_("department"),
    )
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=2,
        choices=Language.choices,
        default=Language.ARABIC,
    )
    must_change_password = models.BooleanField(
        _("must change password"),
        default=False,
    )
    deactivated_at = models.DateTimeField(
        _("deactivated at"),
        blank=True,
        null=True,
    )
    deactivated_by = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="deactivated_users",
        blank=True,
        null=True,
        verbose_name=_("deactivated by"),
    )

    REQUIRED_FIELDS: ClassVar[list[str]] = ["email", "display_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_ci_unique",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(email=""),
                name="accounts_user_email_not_empty",
            ),
            models.CheckConstraint(
                condition=~models.Q(display_name=""),
                name="accounts_user_display_name_not_empty",
            ),
        ]
        permissions = (
            ("manage_accounts", "Can administer internal accounts"),
            ("view_all_directory", "Can view the complete active directory"),
            (
                "view_department_directory",
                "Can view the active directory for own department",
            ),
            ("view_own_profile", "Can view own account profile"),
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Normalize approved identity fields without altering display names."""
        self.username = normalize_username(self.username)
        self.email = normalize_email(self.email)
        self.display_name = self.display_name.strip()
        self.search_key = normalize_account_search(
            f"{self.username} {self.email} {self.display_name}"
        )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Prevent account hard deletion through normal application paths."""
        del args, kwargs
        raise PermissionDenied("User accounts cannot be hard-deleted.")

    def __str__(self) -> str:
        """Use the approved display name while retaining a stable username."""
        return self.display_name or self.username


class LoginThrottle(models.Model):
    """Temporary hashed counters for database-backed login throttling."""

    class Scope(models.TextChoices):
        ACCOUNT = "account", _("Account")
        IP_ADDRESS = "ip", _("IP address")

    scope = models.CharField(max_length=16, choices=Scope.choices)
    key_hash = models.CharField(max_length=64)
    window_started_at = models.DateTimeField()
    failure_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions: ClassVar[tuple[str, ...]] = ()
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=("scope", "key_hash"),
                name="accounts_login_throttle_scope_key_unique",
            )
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=("locked_until",),
                name="accounts_login_locked_idx",
            )
        ]

    def __str__(self) -> str:
        """Return only non-sensitive throttle metadata."""
        return f"{self.scope}:{self.failure_count}"
