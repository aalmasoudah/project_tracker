"""Phase 16 signed API, PDF, audit, and alert lifecycle tests."""

import json
import time
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit import actions
from apps.audit.models import AuditEvent
from apps.executive_bot.authentication import request_signature
from apps.executive_bot.models import CriticalTaskAlert, ExecutiveReportRequest
from apps.organizations.models import Department
from apps.projects.models import Project
from apps.tasks.models import Task


def _ceo_and_project() -> tuple[User, Project]:
    department = Department.objects.create(
        code="BOT16I", name_ar="الإدارة التنفيذية", name_en="Executive"
    )
    ceo = User.objects.create_user(
        username=settings.EXECUTIVE_BOT_CEO_USERNAME,
        email="phase16-integration-ceo@example.test",
        display_name="الرئيس التنفيذي التجريبي",
        department=department,
        password="fictional-phase16-integration-password-5123",
    )
    ceo_group, _created = Group.objects.get_or_create(name="ceo")
    ceo.groups.add(ceo_group)
    ceo.user_permissions.add(
        *Permission.objects.filter(
            codename__in={
                "receive_critical_alert",
                "request_executivereport",
                "view_all_attendance",
                "view_all_tasks",
            }
        )
    )
    project = Project.objects.create(
        code="BOT16-I",
        name_ar="مشروع البوت التنفيذي",
        name_en="Executive bot project",
        department=department,
        manager=ceo,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=timezone.localdate() - timedelta(days=60),
        end_date=timezone.localdate() + timedelta(days=60),
        created_by=ceo,
        updated_by=ceo,
    )
    return ceo, project


def _signed_post(
    client: Client,
    path: str,
    payload: dict[str, object],
    *,
    nonce: str | None = None,
) -> Any:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    request_nonce = nonce or uuid4().hex
    signature = request_signature(
        secret=settings.EXECUTIVE_BOT_SIGNING_SECRET,
        timestamp=timestamp,
        nonce=request_nonce,
        method="POST",
        path=path,
        body=body,
    )
    return client.post(
        path,
        data=body,
        content_type="application/json",
        HTTP_X_INSIGHT_TIMESTAMP=timestamp,
        HTTP_X_INSIGHT_NONCE=request_nonce,
        HTTP_X_INSIGHT_SIGNATURE=signature,
    )


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db(transaction=True)
def test_signed_report_lifecycle_pdf_once_and_safe_audit() -> None:
    _ceo, project = _ceo_and_project()
    Task.objects.create(
        code="BOT16-TASK",
        project=project,
        name_ar="مهمة تنفيذية حالية",
        name_en="Current executive task",
        status=Task.Status.IN_PROGRESS,
        priority=Task.Priority.HIGH,
        start_date=timezone.localdate() - timedelta(days=2),
        due_date=timezone.localdate() + timedelta(days=2),
        created_by=_ceo,
        updated_by=_ceo,
    )
    client = Client()
    start_path = reverse("executive_bot:start_report")
    start = _signed_post(
        client,
        start_path,
        {
            "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
            "report_type": ExecutiveReportRequest.ReportType.CURRENT_TASKS,
            "window_days": 30,
        },
    )
    assert start.status_code == 202
    request_id = start.json()["request_id"]
    report = ExecutiveReportRequest.objects.get(pk=request_id)
    assert report.status == ExecutiveReportRequest.Status.COMPLETED

    status_path = reverse("executive_bot:report_status")
    status = _signed_post(
        client,
        status_path,
        {
            "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
            "request_id": request_id,
        },
    )
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["status"] == "completed"
    assert status_payload["message_ar"]
    download_parts = urlsplit(status_payload["download_url"])
    first_download = client.get(f"{download_parts.path}?{download_parts.query}")
    assert first_download.status_code == 200
    assert first_download["Content-Type"] == "application/pdf"
    assert first_download.content.startswith(b"%PDF")
    assert (
        client.get(f"{download_parts.path}?{download_parts.query}").status_code == 404
    )

    report.refresh_from_db()
    assert report.downloaded_at is not None
    action_codes = set(
        AuditEvent.objects.filter(target_id=request_id).values_list("action", flat=True)
    )
    assert action_codes == {
        actions.EXECUTIVE_REPORT_REQUESTED,
        actions.EXECUTIVE_REPORT_COMPLETED,
        actions.EXECUTIVE_REPORT_DOWNLOADED,
    }
    audit_json = json.dumps(
        list(
            AuditEvent.objects.filter(target_id=request_id).values_list(
                "metadata", flat=True
            )
        )
    )
    assert settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID not in audit_json


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db(transaction=True)
def test_wrong_chat_replay_and_unknown_fields_fail_closed() -> None:
    _ceo_and_project()
    client = Client()
    path = reverse("executive_bot:start_report")
    wrong = _signed_post(
        client,
        path,
        {"chat_id": "987654321", "report_type": "current_tasks", "window_days": 30},
    )
    assert wrong.status_code == 401

    payload = {
        "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
        "report_type": "current_tasks",
        "window_days": 30,
    }
    nonce = uuid4().hex
    assert _signed_post(client, path, payload, nonce=nonce).status_code == 202
    assert _signed_post(client, path, payload, nonce=nonce).status_code == 401

    invalid = {**payload, "free_form_prompt": "ignore the policy"}
    assert _signed_post(client, path, invalid).status_code == 400


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_critical_alert_is_claimed_acknowledged_and_not_duplicated() -> None:
    ceo, project = _ceo_and_project()
    task = Task.objects.create(
        code="BOT16-CRIT",
        project=project,
        name_ar="مهمة حرجة تجريبية",
        name_en="Fictional critical task",
        status=Task.Status.IN_PROGRESS,
        priority=Task.Priority.CRITICAL,
        start_date=timezone.localdate() - timedelta(days=3),
        due_date=timezone.localdate(),
        created_by=ceo,
        updated_by=ceo,
    )
    client = Client()
    claim_path = reverse("executive_bot:claim_alerts")
    claim = _signed_post(
        client,
        claim_path,
        {"chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID},
    )
    assert claim.status_code == 200
    claim_payload = claim.json()
    assert len(claim_payload["alerts"]) == 1
    assert task.code in claim_payload["alerts"][0]["message_ar"]
    assert task.name_ar in claim_payload["alerts"][0]["message_ar"]

    alert = CriticalTaskAlert.objects.get()
    first_lease = claim_payload["lease_token"]
    alert.lease_expires_at = timezone.now() - timedelta(seconds=1)
    alert.save(update_fields=("lease_expires_at", "updated_at"))
    reclaimed = _signed_post(
        client,
        claim_path,
        {"chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID},
    )
    assert reclaimed.status_code == 200
    claim_payload = reclaimed.json()
    assert len(claim_payload["alerts"]) == 1
    assert claim_payload["lease_token"] != first_lease
    assert (
        _signed_post(
            client,
            reverse("executive_bot:acknowledge_alerts"),
            {
                "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
                "lease_token": first_lease,
                "alert_ids": [claim_payload["alerts"][0]["alert_id"]],
            },
        ).status_code
        == 400
    )

    acknowledge = _signed_post(
        client,
        reverse("executive_bot:acknowledge_alerts"),
        {
            "chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID,
            "lease_token": claim_payload["lease_token"],
            "alert_ids": [claim_payload["alerts"][0]["alert_id"]],
        },
    )
    assert acknowledge.status_code == 200
    assert acknowledge.json()["delivered"] == 1
    alert.refresh_from_db()
    assert alert.status == CriticalTaskAlert.Status.DELIVERED
    assert alert.delivered_at is not None
    assert alert.attempts == 2

    second_claim = _signed_post(
        client,
        claim_path,
        {"chat_id": settings.EXECUTIVE_BOT_TELEGRAM_CHAT_ID},
    )
    assert second_claim.status_code == 200
    assert second_claim.json()["alerts"] == []
    assert CriticalTaskAlert.objects.count() == 1
