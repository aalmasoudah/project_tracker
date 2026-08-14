"""Transactional account lifecycle and profile services."""

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, Subquery
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext as _
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import User, UserAvatar
from apps.accounts.roles import (
    NON_TECHNICAL_ROLE_CODES,
    ROLE_CODES,
    TECHNICAL_ADMIN,
)
from apps.audit import actions
from apps.audit.services import record_audit_event

if TYPE_CHECKING:
    from apps.organizations.models import Department


AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_MAX_DIMENSION = 4096
AVATAR_OUTPUT_SIZE = 512
AVATAR_ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


@dataclass(frozen=True)
class PreparedAvatar:
    """A verified metadata-free derivative ready for private storage."""

    content: bytes
    source_size: int
    content_sha256: str


def prepare_profile_avatar(upload: UploadedFile) -> PreparedAvatar:
    """Decode, verify, orient, crop, and normalize an untrusted image upload."""
    if upload.size is not None and upload.size > AVATAR_MAX_BYTES:
        raise ValidationError(_("The profile picture must not exceed 5 MB."))
    raw = upload.read(AVATAR_MAX_BYTES + 1)
    if len(raw) > AVATAR_MAX_BYTES:
        raise ValidationError(_("The profile picture must not exceed 5 MB."))

    try:
        with Image.open(BytesIO(raw)) as probe:
            source_format = (probe.format or "").upper()
            if source_format not in AVATAR_ALLOWED_FORMATS:
                raise ValidationError(_("Upload a valid JPEG, PNG, or WebP image."))
            width, height = probe.size
            if width < 1 or height < 1:
                raise ValidationError(_("The profile picture is invalid."))
            if width > AVATAR_MAX_DIMENSION or height > AVATAR_MAX_DIMENSION:
                raise ValidationError(
                    _("The profile picture dimensions must not exceed 4096 pixels.")
                )
            probe.verify()

        with Image.open(BytesIO(raw)) as source:
            normalized = ImageOps.exif_transpose(source)
            if "A" in normalized.getbands() or "transparency" in normalized.info:
                normalized = normalized.convert("RGBA")
            else:
                normalized = normalized.convert("RGB")
            avatar = ImageOps.fit(
                normalized,
                (AVATAR_OUTPUT_SIZE, AVATAR_OUTPUT_SIZE),
                method=Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            avatar.save(output, format="WEBP", quality=85, method=6)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as error:
        raise ValidationError(_("Upload a valid JPEG, PNG, or WebP image.")) from error

    content = output.getvalue()
    return PreparedAvatar(
        content=content,
        source_size=len(raw),
        content_sha256=hashlib.sha256(content).hexdigest(),
    )


def managed_role_code(user: User) -> str | None:
    """Return the user's one managed role, or no role for recovery superusers."""
    roles = list(
        user.groups.filter(name__in=ROLE_CODES).values_list("name", flat=True)[:2]
    )
    return roles[0] if len(roles) == 1 else None


def is_technical_administrator(user: User) -> bool:
    """Return whether the actor crosses the approved administration boundary."""
    return user.is_superuser or user.groups.filter(name=TECHNICAL_ADMIN).exists()


def _require_account_administrator(actor: User) -> None:
    if not actor.has_perm("accounts.manage_accounts"):
        raise PermissionDenied(_("Account administration permission is required."))


def _require_manageable_target(actor: User, target: User) -> None:
    _require_account_administrator(actor)
    if target.is_superuser and not actor.is_superuser:
        raise PermissionDenied(_("Only a superuser may manage a superuser account."))


def _validate_role_and_department(
    *,
    actor: User,
    role_code: str,
    department: "Department | None",
) -> None:
    if role_code not in ROLE_CODES:
        raise ValidationError(_("Select an approved predefined role."))
    if role_code == TECHNICAL_ADMIN and not actor.is_superuser:
        raise PermissionDenied(_("Only a superuser may assign Technical Admin."))
    if role_code in NON_TECHNICAL_ROLE_CODES and department is None:
        raise ValidationError(_("A department is required for this role."))
    if department is not None and department.is_archived:
        raise ValidationError(_("Archived departments cannot receive users."))


def _assign_managed_role(*, actor: User, target: User, role_code: str) -> None:
    current_role = managed_role_code(target)
    if (
        current_role == TECHNICAL_ADMIN
        and role_code != TECHNICAL_ADMIN
        and not actor.is_superuser
    ):
        raise PermissionDenied(_("Only a superuser may revoke Technical Admin."))
    role = target.groups.model.objects.get(name=role_code)
    target.groups.set([role])


def revoke_user_sessions(
    user: User,
    *,
    exclude_session_key: str | None = None,
) -> int:
    """Delete all database sessions belonging to a user except an optional one."""
    session_keys: list[str] = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if exclude_session_key and session.session_key == exclude_session_key:
            continue
        try:
            session_data = session.get_decoded()
        except Exception:
            continue
        if str(session_data.get(SESSION_KEY, "")) == str(user.pk):
            session_keys.append(session.session_key)
    if not session_keys:
        return 0
    deleted, _details = Session.objects.filter(session_key__in=session_keys).delete()
    return deleted


@transaction.atomic
def create_account(
    *,
    actor: User,
    username: str,
    email: str,
    display_name: str,
    department: "Department | None",
    role_code: str,
    preferred_language: str,
    temporary_password: str,
    request: HttpRequest | None = None,
) -> User:
    """Create one internal account with exactly one approved role."""
    _require_account_administrator(actor)
    _validate_role_and_department(
        actor=actor,
        role_code=role_code,
        department=department,
    )
    user = User.objects.create_user(
        username=username,
        email=email,
        display_name=display_name,
        department=department,
        preferred_language=preferred_language,
        must_change_password=True,
        password=temporary_password,
    )
    _assign_managed_role(actor=actor, target=user, role_code=role_code)
    record_audit_event(
        actor=actor,
        action=actions.ACCOUNT_CREATED,
        target_type="account",
        target_id=str(user.pk),
        target_label=user.display_name,
        metadata={
            "department_id": user.department_id,
            "role": role_code,
        },
        request=request,
    )
    return user


@transaction.atomic
def update_account(
    *,
    actor: User,
    target: User,
    email: str,
    display_name: str,
    department: "Department | None",
    role_code: str,
    preferred_language: str,
    request: HttpRequest | None = None,
) -> User:
    """Update approved profile fields and the exact managed role."""
    _require_manageable_target(actor, target)
    _validate_role_and_department(
        actor=actor,
        role_code=role_code,
        department=department,
    )
    previous_role = managed_role_code(target)
    if (
        previous_role == TECHNICAL_ADMIN
        and not actor.is_superuser
        and role_code != previous_role
    ):
        raise PermissionDenied(_("Only a superuser may change Technical Admin."))

    changed_fields: list[str] = []
    for field_name, new_value in (
        ("email", email),
        ("display_name", display_name),
        ("department", department),
        ("preferred_language", preferred_language),
    ):
        if getattr(target, field_name) != new_value:
            setattr(target, field_name, new_value)
            changed_fields.append(field_name)

    if changed_fields:
        target.save()
    if previous_role != role_code:
        _assign_managed_role(actor=actor, target=target, role_code=role_code)
        changed_fields.append("role")

    if changed_fields:
        record_audit_event(
            actor=actor,
            action=actions.ACCOUNT_UPDATED,
            target_type="account",
            target_id=str(target.pk),
            target_label=target.display_name,
            metadata={"changed_fields": changed_fields},
            request=request,
        )
    return target


def _active_administrator_count() -> int:
    administrator_ids = (
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name=TECHNICAL_ADMIN))
        .values("pk")
        .distinct()
    )
    return len(
        list(
            User.objects.select_for_update()
            .filter(pk__in=Subquery(administrator_ids))
            .values_list("pk", flat=True)
        )
    )


@transaction.atomic
def deactivate_account(
    *,
    actor: User,
    target: User,
    request: HttpRequest | None = None,
) -> User:
    """Deactivate an account and revoke all sessions immediately."""
    _require_manageable_target(actor, target)
    target = User.objects.select_for_update().get(pk=target.pk)
    if actor.pk == target.pk:
        raise ValidationError(_("You cannot deactivate your own account."))
    if is_technical_administrator(target) and _active_administrator_count() <= 1:
        raise ValidationError(
            _("The final active administrator cannot be deactivated.")
        )
    if not target.is_active:
        return target

    target.is_active = False
    target.deactivated_at = timezone.now()
    target.deactivated_by = actor
    target.save(
        update_fields=("is_active", "deactivated_at", "deactivated_by"),
    )
    revoked_sessions = revoke_user_sessions(target)
    record_audit_event(
        actor=actor,
        action=actions.ACCOUNT_DEACTIVATED,
        target_type="account",
        target_id=str(target.pk),
        target_label=target.display_name,
        metadata={"revoked_sessions": revoked_sessions},
        request=request,
    )
    return target


@transaction.atomic
def reactivate_account(
    *,
    actor: User,
    target: User,
    request: HttpRequest | None = None,
) -> User:
    """Reactivate a valid account without restoring any previous session."""
    _require_manageable_target(actor, target)
    target = User.objects.select_for_update().get(pk=target.pk)
    role_code = managed_role_code(target)
    if not target.is_superuser:
        if role_code is None:
            raise ValidationError(_("Assign one approved role before reactivation."))
        _validate_role_and_department(
            actor=actor,
            role_code=role_code,
            department=target.department,
        )
    if target.is_active:
        return target

    target.is_active = True
    target.deactivated_at = None
    target.deactivated_by = None
    target.save(
        update_fields=("is_active", "deactivated_at", "deactivated_by"),
    )
    record_audit_event(
        actor=actor,
        action=actions.ACCOUNT_REACTIVATED,
        target_type="account",
        target_id=str(target.pk),
        target_label=target.display_name,
        request=request,
    )
    return target


@transaction.atomic
def reset_account_password(
    *,
    actor: User,
    target: User,
    temporary_password: str,
    request: HttpRequest | None = None,
) -> User:
    """Set a temporary password, force replacement, and revoke all sessions."""
    _require_manageable_target(actor, target)
    if actor.pk == target.pk:
        raise ValidationError(_("Use the personal password-change page."))
    target.set_password(temporary_password)
    target.must_change_password = True
    target.save(update_fields=("password", "must_change_password"))
    revoked_sessions = revoke_user_sessions(target)
    record_audit_event(
        actor=actor,
        action=actions.PASSWORD_RESET,
        target_type="account",
        target_id=str(target.pk),
        target_label=target.display_name,
        metadata={"revoked_sessions": revoked_sessions},
        request=request,
    )
    return target


@transaction.atomic
def complete_own_password_change(
    *,
    user: User,
    current_session_key: str | None,
    request: HttpRequest | None = None,
) -> None:
    """Clear the temporary-password flag and revoke other sessions."""
    user.must_change_password = False
    user.save(update_fields=("must_change_password",))
    revoked_sessions = revoke_user_sessions(
        user,
        exclude_session_key=current_session_key,
    )
    record_audit_event(
        actor=user,
        action=actions.PASSWORD_CHANGED,
        target_type="account",
        target_id=str(user.pk),
        target_label=user.display_name,
        metadata={"revoked_other_sessions": revoked_sessions},
        request=request,
    )


@transaction.atomic
def update_language_preference(
    *,
    user: User,
    language_code: str,
    request: HttpRequest | None = None,
) -> None:
    """Persist an approved language switch for an authenticated user."""
    if language_code not in User.Language.values:
        raise ValidationError(_("Unsupported language."))
    if user.preferred_language == language_code:
        return
    user.preferred_language = language_code
    user.save(update_fields=("preferred_language",))
    record_audit_event(
        actor=user,
        action=actions.LANGUAGE_CHANGED,
        target_type="account",
        target_id=str(user.pk),
        target_label=user.display_name,
        metadata={"language": language_code},
        request=request,
    )


@transaction.atomic
def update_profile_avatar(
    *,
    actor: User,
    upload: UploadedFile,
    request: HttpRequest | None = None,
) -> UserAvatar:
    """Replace the actor's displayed avatar while retaining prior evidence."""
    if not actor.is_active:
        raise PermissionDenied(_("An active account is required."))
    prepared = prepare_profile_avatar(upload)
    locked_actor = User.objects.select_for_update().get(pk=actor.pk)
    now = timezone.now()
    previous = list(
        UserAvatar.objects.select_for_update().filter(
            user=locked_actor,
            is_active=True,
        )
    )
    for avatar in previous:
        avatar.is_active = False
        avatar.deactivated_at = now
        avatar.deactivated_by = locked_actor
        avatar.save(
            update_fields=("is_active", "deactivated_at", "deactivated_by"),
        )

    avatar = UserAvatar(
        user=locked_actor,
        content_sha256=prepared.content_sha256,
        source_size=prepared.source_size,
    )
    avatar.image.save("avatar.webp", ContentFile(prepared.content), save=False)
    avatar.save()
    record_audit_event(
        actor=locked_actor,
        action=actions.PROFILE_AVATAR_UPDATED,
        target_type="account_avatar",
        target_id=str(avatar.pk),
        target_label=locked_actor.display_name,
        metadata={"replaced_count": len(previous), "source_size": avatar.source_size},
        request=request,
    )
    return avatar


@transaction.atomic
def deactivate_profile_avatar(
    *,
    actor: User,
    request: HttpRequest | None = None,
) -> bool:
    """Hide the actor's avatar and retain its protected record and file."""
    if not actor.is_active:
        raise PermissionDenied(_("An active account is required."))
    locked_actor = User.objects.select_for_update().get(pk=actor.pk)
    avatar = (
        UserAvatar.objects.select_for_update()
        .filter(user=locked_actor, is_active=True)
        .first()
    )
    if avatar is None:
        return False
    avatar.is_active = False
    avatar.deactivated_at = timezone.now()
    avatar.deactivated_by = locked_actor
    avatar.save(update_fields=("is_active", "deactivated_at", "deactivated_by"))
    record_audit_event(
        actor=locked_actor,
        action=actions.PROFILE_AVATAR_REMOVED,
        target_type="account_avatar",
        target_id=str(avatar.pk),
        target_label=locked_actor.display_name,
        request=request,
    )
    return True
