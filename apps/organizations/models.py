"""Department models for the approved organization lifecycle."""

from typing import Any, ClassVar

from django.core.exceptions import PermissionDenied
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.normalization import normalize_account_search


class Department(models.Model):
    """A bilingual organization unit archived instead of deleted."""

    code = models.CharField(
        _("code"),
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Z][A-Z0-9_-]*$",
                message=_(
                    "Use 2-20 uppercase English letters, numbers, underscores, "
                    "or hyphens, starting with a letter."
                ),
            )
        ],
    )
    name_ar = models.CharField(_("Arabic name"), max_length=150)
    name_en = models.CharField(_("English name"), max_length=150)
    search_key = models.CharField(max_length=350, editable=False, db_index=True)
    is_archived = models.BooleanField(_("archived"), default=False, db_index=True)
    archived_at = models.DateTimeField(_("archived at"), blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("code",)
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_archived=False, archived_at__isnull=True)
                    | models.Q(is_archived=True, archived_at__isnull=False)
                ),
                name="organizations_department_archive_state_valid",
            )
        ]
        permissions = (
            ("archive_department", "Can archive departments"),
            ("restore_department", "Can restore departments"),
            ("view_all_departments", "Can view all active departments"),
        )

    def __str__(self) -> str:
        return f"{self.code} - {self.name_en}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Normalize the stable code and harmless surrounding whitespace."""
        self.code = self.code.strip().upper()
        self.name_ar = self.name_ar.strip()
        self.name_en = self.name_en.strip()
        self.search_key = normalize_account_search(
            f"{self.code} {self.name_ar} {self.name_en}"
        )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Prevent department hard deletion through application paths."""
        del args, kwargs
        raise PermissionDenied("Departments cannot be hard-deleted.")

    def localized_name(self, language_code: str) -> str:
        """Return the approved language-specific department name."""
        return self.name_ar if language_code == "ar" else self.name_en
