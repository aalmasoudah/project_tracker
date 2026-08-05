"""Phase 16 signing, privacy-boundary, and configuration unit tests."""

import json
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.http import HttpRequest
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import User
from apps.attendance.models import (
    AttendanceEntry,
    AttendanceSubmission,
    Session,
    SessionParticipant,
    TrainerLink,
)
from apps.courses.models import Course, Trainer
from apps.executive_bot.authentication import (
    IntegrationAuthenticationError,
    authenticate_signed_request,
    request_signature,
)
from apps.executive_bot.evidence import build_executive_evidence
from apps.executive_bot.models import ExecutiveReportRequest, N8nRequestNonce
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.trainees.models import CourseEnrollment, Trainee

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2]
    / "deploy"
    / "n8n"
    / "insight_ceo_telegram_reports.json"
)


def _ceo() -> User:
    department = Department.objects.create(
        code="BOT16U", name_ar="الإدارة التنفيذية", name_en="Executive"
    )
    actor = User.objects.create_user(
        username=settings.EXECUTIVE_BOT_CEO_USERNAME,
        email="phase16-unit-ceo@example.test",
        display_name="الرئيس التنفيذي التجريبي",
        department=department,
        password="fictional-phase16-unit-password-4412",
    )
    ceo_group, _created = Group.objects.get_or_create(name="ceo")
    actor.groups.add(ceo_group)
    actor.user_permissions.add(
        *Permission.objects.filter(
            codename__in={"request_executivereport", "view_all_attendance"},
        )
    )
    return actor


def _signed_request(
    payload: dict[str, object],
    *,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> HttpRequest:
    path = "/integrations/n8n/telegram/reports/start/"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    request_timestamp = timestamp or str(int(time.time()))
    request_nonce = nonce or uuid4().hex
    signature = request_signature(
        secret=settings.EXECUTIVE_BOT_SIGNING_SECRET,
        timestamp=request_timestamp,
        nonce=request_nonce,
        method="POST",
        path=path,
        body=body,
    )
    return RequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        HTTP_X_INSIGHT_TIMESTAMP=request_timestamp,
        HTTP_X_INSIGHT_NONCE=request_nonce,
        HTTP_X_INSIGHT_SIGNATURE=signature,
    )


@pytest.mark.django_db
def test_signed_request_authenticates_exact_ceo_chat_and_rejects_replay() -> None:
    actor = _ceo()
    payload = {
        "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
        "report_type": "current_tasks",
        "window_days": 30,
    }
    nonce = uuid4().hex
    authenticated = authenticate_signed_request(_signed_request(payload, nonce=nonce))
    assert authenticated.actor == actor
    assert authenticated.payload == payload
    assert N8nRequestNonce.objects.count() == 1
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(_signed_request(payload, nonce=nonce))


@pytest.mark.django_db
def test_signed_request_rejects_wrong_chat_without_storing_raw_values() -> None:
    _ceo()
    wrong_chat = "987654321"
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(
            _signed_request(
                {
                    "chat_id": wrong_chat,
                    "report_type": "attendance",
                    "window_days": 30,
                }
            )
        )
    assert not N8nRequestNonce.objects.filter(digest__icontains=wrong_chat).exists()


@pytest.mark.django_db
def test_signed_request_rejects_expired_oversized_inactive_and_wrong_role() -> None:
    actor = _ceo()
    payload = {
        "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
        "report_type": "current_tasks",
        "window_days": 30,
    }
    expired = str(
        int(time.time()) - int(settings.EXECUTIVE_BOT_SIGNATURE_TTL_SECONDS) - 1
    )
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(_signed_request(payload, timestamp=expired))

    oversized = {**payload, "padding": "x" * settings.EXECUTIVE_BOT_MAX_BODY_BYTES}
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(_signed_request(oversized))

    actor.groups.clear()
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(_signed_request(payload))

    ceo_group = Group.objects.get(name="ceo")
    actor.groups.add(ceo_group)
    actor.is_active = False
    actor.save(update_fields=("is_active",))
    with pytest.raises(IntegrationAuthenticationError):
        authenticate_signed_request(_signed_request(payload))


@pytest.mark.django_db
def test_attendance_names_stay_in_pdf_rows_and_never_enter_provider_payload() -> None:
    ceo = _ceo()
    assert ceo.department is not None
    project = Project.objects.create(
        code="BOT16-P",
        name_ar="مشروع التقرير التنفيذي",
        name_en="Executive report project",
        department=ceo.department,
        manager=ceo,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=timezone.localdate() - timedelta(days=60),
        end_date=timezone.localdate() + timedelta(days=60),
        created_by=ceo,
        updated_by=ceo,
    )
    course = Course.objects.create(
        code="BOT16-C",
        project=project,
        name_ar="دورة آمنة",
        name_en="Safe course",
        delivery_type=Course.DeliveryType.ONLINE,
        capacity=5,
        start_at=timezone.now() - timedelta(days=30),
        end_at=timezone.now() + timedelta(days=30),
        status=Course.Status.ACTIVE,
        created_by=ceo,
        updated_by=ceo,
    )
    trainer = Trainer.objects.create(
        code="BOT16-T",
        name_ar="مدرب تجريبي",
        name_en="Fictional trainer",
        email="phase16-trainer@example.test",
        created_by=ceo,
        updated_by=ceo,
    )
    trainee = Trainee.objects.create(
        full_name="نورة المتدربة",
        phone="0509999999",
        email="noura.private@example.test",
        created_by=ceo,
        updated_by=ceo,
    )
    enrollment = CourseEnrollment.objects.create(
        course=course,
        trainee=trainee,
        trainee_number=1,
        created_by=ceo,
    )
    session = Session.objects.create(
        course=course,
        trainer=trainer,
        title_ar="جلسة الحضور",
        title_en="Attendance session",
        start_at=timezone.now() - timedelta(days=1, hours=2),
        end_at=timezone.now() - timedelta(days=1),
        created_by=ceo,
        updated_by=ceo,
    )
    participant = SessionParticipant.objects.create(
        session=session,
        enrollment=enrollment,
    )
    link = TrainerLink.objects.create(
        session=session,
        token_hash="a" * 64,
        state=TrainerLink.State.SUBMITTED,
        expires_at=timezone.now() + timedelta(hours=1),
        issued_by=ceo,
    )
    submission = AttendanceSubmission.objects.create(
        session=session,
        trainer_link=link,
        state=AttendanceSubmission.State.APPROVED,
        trainer_notes="معلومة خاصة لا تظهر",
    )
    AttendanceEntry.objects.create(
        submission=submission,
        participant=participant,
        value=AttendanceEntry.Value.PRESENT,
        notes="ملاحظة خاصة لا تظهر",
    )

    evidence = build_executive_evidence(
        actor=ceo,
        report_type=ExecutiveReportRequest.ReportType.ATTENDANCE,
        window_days=30,
    )
    provider_json = json.dumps(evidence.provider_payload, ensure_ascii=False)
    rows_json = json.dumps(evidence.document.rows, ensure_ascii=False)
    assert trainee.full_name in rows_json
    assert trainee.full_name not in provider_json
    assert trainee.phone not in provider_json
    assert trainee.email not in provider_json
    assert trainee.phone not in rows_json
    assert trainee.email not in rows_json
    assert submission.trainer_notes not in rows_json
    assert "ملاحظة خاصة لا تظهر" not in rows_json


def test_n8n_workflow_is_inactive_private_and_covers_fixed_arabic_commands() -> None:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(workflow, ensure_ascii=False)
    node_types = {node["type"] for node in workflow["nodes"]}
    node_names = {node["name"] for node in workflow["nodes"]}

    assert workflow["active"] is False
    assert workflow["settings"]["saveDataSuccessExecution"] == "none"
    assert workflow["settings"]["saveDataErrorExecution"] == "none"
    assert workflow["settings"]["saveExecutionProgress"] is False
    assert "n8n-nodes-base.telegramTrigger" in node_types
    assert "n8n-nodes-base.scheduleTrigger" in node_types
    assert "Send Arabic PDF" in node_names
    assert "Acknowledge Critical Alert" in node_names
    assert all(
        command in serialized
        for command in ("/tasks", "/overdue", "/attendance", "/help")
    )
    assert all(
        endpoint in serialized
        for endpoint in (
            "/reports/start/",
            "/reports/status/",
            "/alerts/claim/",
            "/alerts/acknowledge/",
        )
    )
    assert "createHmac('sha256'" in serialized
    assert "String(alert.alert_id)" in serialized
    assert "INSIGHT_N8N_SIGNING_SECRET" in serialized
    assert "INSIGHT_TELEGRAM_CEO_CHAT_ID" in serialized
    assert "telegramApi" not in workflow
    assert "bot_token" not in serialized.lower()
    assert "groq_api_key" not in serialized.lower()
