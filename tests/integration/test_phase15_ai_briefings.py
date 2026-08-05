"""Phase 15 lifecycle, permission, evidence, notification, and UI coverage."""

from datetime import date, timedelta
from importlib import import_module
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_briefings.evidence import build_project_evidence
from apps.ai_briefings.models import AIBriefing, AIBriefingSource
from apps.ai_briefings.services import (
    generate_briefing,
    recover_stale_briefings,
    request_briefing,
    review_briefing,
)
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.notifications.models import Notification
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.tasks.models import Task, TaskComment

ROLE_PERMISSIONS = cast(
    "dict[str, set[str]]",
    import_module(
        "apps.ai_briefings.migrations.0002_seed_phase15_permissions"
    ).ROLE_PERMISSIONS,
)
PASSWORD = "fictional-phase15-password-8294"


def role_user(username: str, role: str, department: Department) -> User:
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        display_name=username.replace("-", " ").title(),
        department=department,
        preferred_language=User.Language.ENGLISH,
        password=PASSWORD,
    )
    user.groups.add(Group.objects.get(name=role))
    return user


def active_project(code: str, manager: User, department: Department) -> Project:
    return Project.objects.create(
        code=code,
        name_ar=f"مشروع {code}",
        name_en=f"Project {code}",
        department=department,
        manager=manager,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        budget=999_999,
        goals="Private project goals",
        requirements="Private requirements",
        notes="Private notes",
        created_by=manager,
        updated_by=manager,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_phase15_permissions_match_approved_roles() -> None:
    for role, expected in ROLE_PERMISSIONS.items():
        actual = set(
            Group.objects.get(name=role)
            .permissions.filter(content_type__app_label="ai_briefings")
            .values_list("codename", flat=True)
        )
        assert actual == expected


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_evidence_is_scoped_bounded_and_excludes_sensitive_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    department = Department.objects.create(
        code="AI15-EV", name_ar="إدارة الأدلة", name_en="Evidence"
    )
    manager = role_user("ai-evidence-manager", "project_manager", department)
    project = active_project("AI-EVIDENCE", manager, department)
    blocked = Task.objects.create(
        code="AI-BLOCKED",
        project=project,
        name_ar="مهمة متوقفة",
        name_en="Blocked task",
        description="Do not send this description",
        status=Task.Status.BLOCKED,
        priority=Task.Priority.CRITICAL,
        due_date=date(2026, 8, 1),
        blocking_reason="Dependency unavailable",
        created_by=manager,
        updated_by=manager,
    )
    TaskComment.objects.create(
        task=blocked,
        author=manager,
        body="Do not send this comment",
    )
    monkeypatch.setattr("django.utils.timezone.localdate", lambda: date(2026, 8, 4))

    bundle = build_project_evidence(
        actor=manager,
        project=project,
        language="en",
        window_days=14,
    )
    serialized = str(bundle.payload)

    assert "Blocked task" in serialized
    assert "Dependency unavailable" in serialized
    assert "Do not send this description" not in serialized
    assert "Do not send this comment" not in serialized
    assert "999999" not in serialized
    assert "Private project goals" not in serialized
    assert bundle.allowed_citations == frozenset(
        {f"project:{project.pk}", f"task:{blocked.pk}"}
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_complete_arabic_briefing_lifecycle_is_cited_audited_and_reviewed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    department = Department.objects.create(
        code="AI15-AR", name_ar="إدارة الذكاء", name_en="AI"
    )
    manager = role_user("ai-arabic-manager", "project_manager", department)
    project = active_project("AI-ARABIC", manager, department)
    monkeypatch.setattr(
        "apps.ai_briefings.services._queue_generation",
        lambda briefing_id: None,
    )
    briefing = request_briefing(
        actor=manager,
        project=project,
        language=AIBriefing.Language.ARABIC,
        detail_level=AIBriefing.DetailLevel.EXECUTIVE,
        evidence_window_days=14,
    )

    assert generate_briefing(briefing_id=briefing.pk) == AIBriefing.Status.COMPLETED
    briefing.refresh_from_db()
    assert briefing.output_data["summary"].startswith("ملخص تجريبي")
    assert briefing.provider_code == "fake"
    assert briefing.model_code == "deterministic"
    assert briefing.cached_input_tokens == 0
    assert briefing.sources.filter(source_ref=f"project:{project.pk}").exists()
    assert Notification.objects.filter(
        recipient=manager,
        event_key=f"ai-briefing-ready:{briefing.pk}",
    ).exists()
    assert set(
        AuditEvent.objects.filter(
            target_type="ai_briefing", target_id=str(briefing.pk)
        ).values_list("action", flat=True)
    ) == {actions.AI_BRIEFING_REQUESTED, actions.AI_BRIEFING_COMPLETED}

    reviewed = review_briefing(actor=manager, briefing=briefing)
    assert reviewed.reviewed_by == manager
    assert reviewed.reviewed_at is not None
    assert AuditEvent.objects.filter(
        action=actions.AI_BRIEFING_REVIEWED,
        target_id=str(briefing.pk),
    ).exists()


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_briefing_routes_hide_cross_project_records_and_recheck_access() -> None:
    department = Department.objects.create(
        code="AI15-ID", name_ar="إدارة العزل", name_en="Isolation"
    )
    owner = role_user("ai-owner", "project_manager", department)
    stranger = role_user("ai-stranger", "project_manager", department)
    employee = role_user("ai-employee", "employee", department)
    project = active_project("AI-PRIVATE", owner, department)
    briefing = AIBriefing.objects.create(
        project=project,
        requested_by=owner,
        language="en",
        detail_level="executive",
        evidence_window_days=14,
    )
    client = Client()

    client.force_login(stranger)
    assert (
        client.get(reverse("ai_briefings:detail", args=(briefing.pk,))).status_code
        == 404
    )
    assert (
        client.get(reverse("ai_briefings:request", args=(project.pk,))).status_code
        == 404
    )

    client.force_login(employee)
    assert (
        client.get(reverse("ai_briefings:detail", args=(briefing.pk,))).status_code
        == 404
    )
    assert (
        client.get(reverse("ai_briefings:request", args=(project.pk,))).status_code
        == 404
    )

    client.force_login(owner)
    assert (
        client.get(reverse("ai_briefings:detail", args=(briefing.pk,))).status_code
        == 200
    )
    owner.groups.clear()
    owner = User.objects.get(pk=owner.pk)
    client.force_login(owner)
    assert (
        client.get(reverse("ai_briefings:detail", args=(briefing.pk,))).status_code
        == 404
    )


@pytest.mark.integration
@pytest.mark.django_db
@override_settings(AI_BRIEFING_DAILY_LIMIT=1)
def test_request_quota_archived_guard_and_protected_retention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    department = Department.objects.create(
        code="AI15-LM", name_ar="إدارة الحدود", name_en="Limits"
    )
    manager = role_user("ai-limit-manager", "project_manager", department)
    project = active_project("AI-LIMIT", manager, department)
    monkeypatch.setattr(
        "apps.ai_briefings.services._queue_generation",
        lambda briefing_id: None,
    )
    briefing = request_briefing(
        actor=manager,
        project=project,
        language="en",
        detail_level="operational",
        evidence_window_days=7,
    )
    with pytest.raises(ValidationError):
        request_briefing(
            actor=manager,
            project=project,
            language="en",
            detail_level="operational",
            evidence_window_days=7,
        )
    with pytest.raises(PermissionDenied):
        briefing.delete()
    source = AIBriefingSource.objects.create(
        briefing=briefing,
        source_ref=f"project:{project.pk}",
        source_type="project",
        source_id=str(project.pk),
        source_label=project.code,
    )
    with pytest.raises(PermissionDenied):
        source.delete()
    project.is_archived = True
    project.archived_at = briefing.created_at
    project.archived_by = manager
    project.save(update_fields=("is_archived", "archived_at", "archived_by"))
    with pytest.raises(PermissionDenied):
        request_briefing(
            actor=manager,
            project=project,
            language="en",
            detail_level="executive",
            evidence_window_days=14,
        )


@pytest.mark.integration
@pytest.mark.django_db
def test_project_and_completed_briefing_pages_render_actions_and_citations() -> None:
    department = Department.objects.create(
        code="AI15-UI", name_ar="إدارة الواجهة", name_en="Interface"
    )
    manager = role_user("ai-ui-manager", "project_manager", department)
    project = active_project("AI-UI", manager, department)
    briefing = AIBriefing.objects.create(
        project=project,
        requested_by=manager,
        language="en",
        detail_level="executive",
        evidence_window_days=14,
        status=AIBriefing.Status.COMPLETED,
        output_data={
            "summary": "Project summary",
            "highlights": [
                {"text": "Project is active.", "citations": [f"project:{project.pk}"]}
            ],
            "risks": [],
            "upcoming": [],
            "recommended_actions": [],
            "data_gaps": [],
        },
        provider_code="fake",
        model_code="deterministic",
        prompt_version="project-briefing-v1",
        input_fingerprint="a" * 64,
        evidence_count=1,
        started_at=project.created_at,
        completed_at=project.created_at,
    )
    AIBriefingSource.objects.create(
        briefing=briefing,
        source_ref=f"project:{project.pk}",
        source_type="project",
        source_id=str(project.pk),
        source_label=project.code,
        source_updated_at=project.updated_at,
    )
    client = Client()
    client.cookies["insight_language"] = "en"
    client.force_login(manager)

    project_page = client.get(reverse("projects:detail", args=(project.pk,)))
    assert project_page.status_code == 200
    assert (
        reverse("ai_briefings:request", args=(project.pk,))
        in project_page.content.decode()
    )
    detail = client.get(reverse("ai_briefings:detail", args=(briefing.pk,)))
    content = detail.content.decode()
    assert detail.status_code == 200
    assert "Project summary" in content
    assert reverse("projects:detail", args=(project.pk,)) in content
    assert "Mark as reviewed" in content
    assert (
        client.get(reverse("ai_briefings:status", args=(briefing.pk,))).status_code
        == 200
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_processing_jobs_are_idempotent_and_only_stale_work_is_requeued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    department = Department.objects.create(
        code="AI15-JB", name_ar="إدارة المهام", name_en="Jobs"
    )
    manager = role_user("ai-job-manager", "project_manager", department)
    project = active_project("AI-JOBS", manager, department)
    current = AIBriefing.objects.create(
        project=project,
        requested_by=manager,
        language="en",
        detail_level="executive",
        evidence_window_days=14,
        status=AIBriefing.Status.PROCESSING,
        started_at=timezone.now(),
    )
    stale = AIBriefing.objects.create(
        project=project,
        requested_by=manager,
        language="en",
        detail_level="executive",
        evidence_window_days=14,
        status=AIBriefing.Status.PROCESSING,
        started_at=timezone.now() - timedelta(minutes=20),
    )
    queued: list[int] = []
    monkeypatch.setattr(
        "apps.ai_briefings.services._queue_generation",
        queued.append,
    )

    assert generate_briefing(briefing_id=current.pk) == AIBriefing.Status.PROCESSING
    assert recover_stale_briefings() == 1
    current.refresh_from_db()
    stale.refresh_from_db()
    assert current.status == AIBriefing.Status.PROCESSING
    assert stale.status == AIBriefing.Status.QUEUED
    assert stale.started_at is None
    assert queued == [stale.pk]
