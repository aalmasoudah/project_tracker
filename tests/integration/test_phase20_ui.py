"""Phase 20 application-shell, progress, and avatar integration coverage."""

from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User, UserAvatar
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.organizations.models import Department
from apps.projects.models import Project


def _user(*, username: str, display_name: str) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=display_name,
        password="fictional-phase20-password",
    )
    user.user_permissions.add(Permission.objects.get(codename="view_own_profile"))
    return user


def _image_upload(
    *,
    name: str = "profile.png",
    color: tuple[int, int, int] = (10, 64, 12),
) -> SimpleUploadedFile:
    output = BytesIO()
    Image.new("RGB", (640, 480), color).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


@pytest.mark.integration
@pytest.mark.django_db
def test_authenticated_shell_has_sidebar_profile_footer_and_active_page(
    client: Client,
) -> None:
    user = _user(username="phase20-shell", display_name="Phase Twenty User")
    client.force_login(user)

    response = client.get(reverse("home"))

    content = response.content.decode()
    assert response.status_code == 200
    assert 'id="desktop-navigation"' in content
    assert 'id="mobile-navigation"' in content
    assert 'aria-current="page"' in content
    assert reverse("accounts:profile") in content
    assert "Phase Twenty User" in content
    assert "app-footer" in content

    profile_content = client.get(reverse("accounts:profile")).content.decode()
    assert 'class="app-breadcrumb"' in profile_content
    assert reverse("home") in profile_content


@pytest.mark.integration
@pytest.mark.django_db
def test_navigation_does_not_render_unauthorized_business_links(
    client: Client,
) -> None:
    user = _user(username="phase20-scope", display_name="Scoped User")
    client.force_login(user)

    content = client.get(reverse("home")).content.decode()

    assert reverse("projects:list") not in content
    assert reverse("reports:index") not in content
    assert reverse("audit:list") not in content


@pytest.mark.integration
@pytest.mark.django_db
def test_common_management_journeys_are_available_within_three_clicks(
    client: Client,
) -> None:
    executive = User.objects.create_superuser(
        username="phase20-navigation",
        email="phase20-navigation@example.test",
        display_name="Navigation Executive",
        password="fictional-phase20-password",
    )
    department = Department.objects.create(
        code="NAV20",
        name_ar="إدارة التنقل",
        name_en="Navigation",
    )
    project = Project.objects.create(
        code="PRJ-NAV20",
        name_ar="مشروع التنقل",
        name_en="Navigation project",
        department=department,
        manager=executive,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
        created_by=executive,
        updated_by=executive,
    )
    client.force_login(executive)

    dashboard = client.get(reverse("home")).content.decode()
    for destination in (
        reverse("projects:list"),
        reverse("tasks:list"),
        reverse("approvals:queue"),
        reverse("reports:index"),
        reverse("attendance:list"),
        reverse("trainees:list"),
    ):
        assert destination in dashboard

    assert reverse("tasks:create") in client.get(reverse("tasks:list")).content.decode()
    assert (
        reverse("attendance:create")
        in client.get(reverse("attendance:list")).content.decode()
    )

    project_list = client.get(reverse("projects:list")).content.decode()
    assert reverse("projects:detail", args=(project.pk,)) in project_list
    project_detail = client.get(
        reverse("projects:detail", args=(project.pk,))
    ).content.decode()
    for project_action in (
        reverse("projects:team", args=(project.pk,)),
        reverse("ai_briefings:request", args=(project.pk,)),
        reverse("project_agents:request", args=(project.pk,)),
    ):
        assert project_action in project_detail

    reports = client.get(reverse("reports:index")).content.decode()
    assert reverse("reports:generate") in reports


@pytest.mark.integration
@pytest.mark.django_db
def test_avatar_upload_replace_remove_retains_history(
    client: Client,
    tmp_path: Path,
) -> None:
    user = _user(username="phase20-avatar", display_name="Avatar User")
    client.force_login(user)

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            reverse("accounts:avatar_update"),
            {"avatar": _image_upload()},
        )
        assert response.status_code == 302
        first = UserAvatar.objects.get(user=user, is_active=True)
        first_path = Path(first.image.path)
        assert first_path.is_file()
        with Image.open(first_path) as stored:
            assert stored.format == "WEBP"
            assert stored.size == (512, 512)
            assert not stored.getexif()

        response = client.post(
            reverse("accounts:avatar_update"),
            {"avatar": _image_upload(color=(129, 144, 103))},
        )
        assert response.status_code == 302
        first.refresh_from_db()
        second = UserAvatar.objects.get(user=user, is_active=True)
        assert first.is_active is False
        assert first.deactivated_at is not None
        assert first_path.is_file()
        assert second.pk != first.pk

        response = client.post(reverse("accounts:avatar_remove"))
        assert response.status_code == 302
        second.refresh_from_db()
        assert second.is_active is False
        assert Path(second.image.path).is_file()
        assert UserAvatar.objects.filter(user=user).count() == 2
        assert not UserAvatar.objects.filter(user=user, is_active=True).exists()

    assert (
        AuditEvent.objects.filter(
            actor=user,
            action=actions.PROFILE_AVATAR_UPDATED,
        ).count()
        == 2
    )
    assert (
        AuditEvent.objects.filter(
            actor=user,
            action=actions.PROFILE_AVATAR_REMOVED,
        ).count()
        == 1
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "content_type", "content"),
    [
        ("fake.png", "image/png", b"not an image"),
        ("avatar.svg", "image/svg+xml", b"<svg><script>alert(1)</script></svg>"),
    ],
)
def test_avatar_rejects_deceptive_or_unsupported_uploads(
    client: Client,
    tmp_path: Path,
    name: str,
    content_type: str,
    content: bytes,
) -> None:
    user = _user(username=f"reject-{name[-3:]}", display_name="Rejected Avatar")
    client.force_login(user)

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            reverse("accounts:avatar_update"),
            {"avatar": SimpleUploadedFile(name, content, content_type=content_type)},
        )

    assert response.status_code == 400
    assert not UserAvatar.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_avatar_rejects_upload_larger_than_five_mebibytes(
    client: Client,
    tmp_path: Path,
) -> None:
    user = _user(username="avatar-too-large", display_name="Large Avatar")
    client.force_login(user)
    upload = SimpleUploadedFile(
        "large.png",
        b"\x89PNG\r\n\x1a\n" + (b"0" * (5 * 1024 * 1024)),
        content_type="image/png",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            reverse("accounts:avatar_update"),
            {"avatar": upload},
        )

    assert response.status_code == 400
    assert not UserAvatar.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_avatar_rejects_image_dimensions_over_limit(
    client: Client,
    tmp_path: Path,
) -> None:
    user = _user(username="avatar-too-wide", display_name="Wide Avatar")
    client.force_login(user)
    output = BytesIO()
    Image.new("RGB", (4097, 1), (10, 64, 12)).save(output, format="PNG")
    upload = SimpleUploadedFile(
        "wide.png",
        output.getvalue(),
        content_type="image/png",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        response = client.post(
            reverse("accounts:avatar_update"),
            {"avatar": upload},
        )

    assert response.status_code == 400
    assert not UserAvatar.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_avatar_delivery_rechecks_account_visibility(
    client: Client,
    tmp_path: Path,
) -> None:
    owner = _user(username="avatar-owner", display_name="Avatar Owner")
    other = _user(username="avatar-other", display_name="Avatar Other")
    other_client = Client()
    other_client.force_login(other)

    with override_settings(MEDIA_ROOT=tmp_path):
        client.force_login(owner)
        client.post(
            reverse("accounts:avatar_update"),
            {"avatar": _image_upload()},
        )
        own_response = client.get(reverse("accounts:avatar", args=(owner.pk,)))
        assert own_response.status_code == 200
        assert own_response["Content-Type"] == "image/webp"
        assert own_response["X-Content-Type-Options"] == "nosniff"

        hidden_response = other_client.get(reverse("accounts:avatar", args=(owner.pk,)))
        assert hidden_response.status_code == 404
        own_response.close()


@pytest.mark.integration
@pytest.mark.django_db
def test_avatar_record_cannot_be_deleted() -> None:
    user = _user(username="avatar-retention", display_name="Retained Avatar")
    avatar = UserAvatar(user=user, content_sha256="0" * 64, source_size=1)

    with pytest.raises(PermissionDenied):
        avatar.delete()
