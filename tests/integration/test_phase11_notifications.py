"""Phase 11 notification, background delivery, and authorization tests."""

from datetime import date, timedelta
from typing import cast

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest
from apps.approvals.services import approve_request, submit_completion
from apps.attendance.models import AttendanceReview
from apps.attendance.services import review_attendance
from apps.audit.models import AuditEvent
from apps.notifications.events import generate_task_deadline_notifications
from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    NotificationPreference,
)
from apps.notifications.policies import CATEGORY_POLICIES, MESSAGE_CONTENT
from apps.notifications.services import create_notification, update_preferences
from apps.notifications.tasks import (
    deliver_notification_email,
    dispatch_pending_deliveries,
)
from apps.organizations.models import Department
from apps.projects.models import ProjectMembership
from apps.tasks.services import add_task_comment, replace_task_assignments
from tests.integration.test_phase5_tasks import (
    create_project_task,
    make_project,
    role_user,
)
from tests.integration.test_phase7_approvals import make_task
from tests.integration.test_phase10_attendance_review import create_submission

PHASE11_ROLE_PERMISSIONS = cast(
    "dict[str, set[tuple[str, str]]]",
    {
        "technical_admin": {
            ("deliveryattempt", "view_delivery_status"),
        },
        "ceo": set(),
        "executive_manager": set(),
        "project_manager": set(),
        "supervisor": set(),
        "employee": set(),
        "contractor": set(),
    },
)


@pytest.mark.integration
@pytest.mark.django_db
def test_seeded_phase11_operational_permission_is_technical_admin_only() -> None:
    for role_code, expected in PHASE11_ROLE_PERMISSIONS.items():
        group = Group.objects.get(name=role_code)
        actual = {
            (permission.content_type.model, permission.codename)
            for permission in group.permissions.select_related("content_type").filter(
                content_type__app_label="notifications",
                codename="view_delivery_status",
            )
        }
        assert actual == expected
    department = Department.objects.create(
        code="OPS11",
        name_ar="العمليات",
        name_en="Operations",
    )
    technical_admin = role_user(
        "phase11-technical-admin",
        "technical_admin",
        department,
    )
    employee = role_user("phase11-operations-employee", "employee", department)
    client = Client()
    client.force_login(employee)
    assert client.get(reverse("notifications:deliveries")).status_code == 403
    client.force_login(technical_admin)
    assert client.get(reverse("notifications:deliveries")).status_code == 200


@pytest.mark.integration
@pytest.mark.security
@pytest.mark.django_db
def test_preferences_deduplication_safe_links_and_owner_scope(
    user: User,
) -> None:
    notification = create_notification(
        recipient=user,
        message_code="task_assigned",
        event_key="assignment:phase11:1",
        target_path=reverse("accounts:profile"),
    )
    duplicate = create_notification(
        recipient=user,
        message_code="task_assigned",
        event_key="assignment:phase11:1",
        target_path=reverse("accounts:profile"),
    )
    assert notification is not None
    assert duplicate is None
    assert Notification.objects.count() == 1
    assert DeliveryAttempt.objects.count() == 1

    values = dict.fromkeys(CATEGORY_POLICIES, (True, False))
    values["task_assignment"] = (False, False)
    values["approval"] = (False, False)
    update_preferences(actor=user, values=values)
    assert NotificationPreference.objects.get(
        recipient=user,
        category=Notification.Category.APPROVAL,
    ).in_app_enabled
    assert (
        create_notification(
            recipient=user,
            message_code="task_assigned",
            event_key="assignment:phase11:suppressed",
        )
        is None
    )
    mandatory = create_notification(
        recipient=user,
        message_code="approval_action",
        event_key="approval:phase11:mandatory",
    )
    assert mandatory is not None
    assert mandatory.show_in_app
    assert AuditEvent.objects.filter(
        scope=AuditEvent.Scope.NOTIFICATIONS,
        target_id=str(user.pk),
    ).exists()

    with pytest.raises(ValidationError):
        create_notification(
            recipient=user,
            message_code="mentioned",
            event_key="mention:phase11:unsafe",
            target_path="https://malicious.example.test/",
        )

    other = User.objects.create_user(
        username="notification-outsider",
        email="notification-outsider@example.test",
        display_name="Notification Outsider",
        department=user.department,
        password="fictional-notification-password-8112",
    )
    client = Client()
    client.force_login(other)
    assert (
        client.post(
            reverse("notifications:open", args=[notification.pk]),
        ).status_code
        == 404
    )
    client.force_login(user)
    response = client.post(
        reverse("notifications:open", args=[notification.pk]),
    )
    assert response.status_code == 302
    notification.refresh_from_db()
    assert notification.is_read
    assert notification.read_at is not None
    with pytest.raises(PermissionDenied):
        notification.delete()
    with pytest.raises(PermissionDenied):
        Notification.objects.filter(pk=notification.pk).delete()


@pytest.mark.integration
@pytest.mark.django_db
def test_worker_retries_is_idempotent_and_records_safe_failure(
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = MESSAGE_CONTENT["mentioned"]
    notification = Notification.objects.create(
        recipient=user,
        category=Notification.Category.MENTION,
        message_code="mentioned",
        event_key="worker:phase11:success",
        title_ar=content.title_ar,
        title_en=content.title_en,
        body_ar=content.body_ar,
        body_en=content.body_en,
    )
    delivery = DeliveryAttempt.objects.create(notification=notification)
    sent: list[int] = []

    def fake_send(current: Notification) -> int:
        sent.append(current.pk)
        return 1

    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification_email",
        fake_send,
    )
    assert deliver_notification_email.run(delivery.pk) == DeliveryAttempt.Status.SENT
    assert deliver_notification_email.run(delivery.pk) == DeliveryAttempt.Status.SENT
    delivery.refresh_from_db()
    assert delivery.attempts == 1
    assert delivery.sent_at is not None
    assert sent == [notification.pk]

    failed_notification = Notification.objects.create(
        recipient=user,
        category=Notification.Category.MENTION,
        message_code="mentioned",
        event_key="worker:phase11:failure",
        title_ar=content.title_ar,
        title_en=content.title_en,
        body_ar=content.body_ar,
        body_en=content.body_en,
    )
    failed_delivery = DeliveryAttempt.objects.create(notification=failed_notification)

    def failing_send(current: Notification) -> int:
        del current
        raise ConnectionError("fictional provider outage with private details")

    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification_email",
        failing_send,
    )
    for expected_attempt in range(1, 4):
        with pytest.raises(
            RuntimeError,
            match="Notification email delivery failed",
        ):
            deliver_notification_email.run(failed_delivery.pk)
        failed_delivery.refresh_from_db()
        assert failed_delivery.attempts == expected_attempt
        assert failed_delivery.status == DeliveryAttempt.Status.RETRY
        assert failed_delivery.last_error_code == "ConnectionError"
        failed_delivery.next_attempt_at = timezone.now() - timedelta(seconds=1)
        failed_delivery.save(update_fields=("next_attempt_at",))
    assert (
        deliver_notification_email.run(failed_delivery.pk)
        == DeliveryAttempt.Status.FAILED
    )
    failed_delivery.refresh_from_db()
    assert failed_delivery.attempts == 4
    assert failed_delivery.status == DeliveryAttempt.Status.FAILED
    assert "private details" not in failed_delivery.last_error_code

    interrupted_notification = Notification.objects.create(
        recipient=user,
        category=Notification.Category.MENTION,
        message_code="mentioned",
        event_key="worker:phase11:interrupted",
        title_ar=content.title_ar,
        title_en=content.title_en,
        body_ar=content.body_ar,
        body_en=content.body_en,
    )
    interrupted_delivery = DeliveryAttempt.objects.create(
        notification=interrupted_notification,
        status=DeliveryAttempt.Status.PROCESSING,
        last_attempt_at=None,
    )
    queued: list[int] = []
    monkeypatch.setattr(
        deliver_notification_email,
        "delay",
        queued.append,
    )
    assert dispatch_pending_deliveries.run() == 1
    interrupted_delivery.refresh_from_db()
    assert interrupted_delivery.status == DeliveryAttempt.Status.RETRY
    assert interrupted_delivery.last_error_code == "WorkerInterrupted"
    assert queued == [interrupted_delivery.pk]


@pytest.mark.integration
@pytest.mark.django_db
def test_assignment_mention_and_riyadh_daily_deadline_events(
    department: Department,
) -> None:
    manager = role_user(
        "phase11-task-manager",
        "project_manager",
        department,
    )
    employee = role_user(
        "phase11-task-employee",
        "employee",
        department,
    )
    project = make_project(
        code="PRJ-N11",
        department=department,
        manager=manager,
    )
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    task = create_project_task(
        actor=manager,
        project=project,
        assignee=employee,
        code="TSK-N11",
    )
    assert (
        Notification.objects.filter(
            recipient=employee,
            message_code="task_assigned",
        ).count()
        == 1
    )

    add_task_comment(
        actor=employee,
        task=task,
        body="@phase11-task-manager Please review this update.",
    )
    assert (
        Notification.objects.filter(
            recipient=manager,
            message_code="mentioned",
        ).count()
        == 1
    )
    arabic_username_user = User.objects.create_user(
        username="مراجع_عربي",
        email="phase11-arabic-mention@example.test",
        display_name="مراجع عربي",
        department=department,
        password="fictional-notification-password-8113",
    )
    arabic_username_user.groups.add(Group.objects.get(name="employee"))
    ProjectMembership.objects.create(
        project=project,
        user=arabic_username_user,
        added_by=manager,
    )
    replace_task_assignments(
        actor=manager,
        task=task,
        assignees=[employee, arabic_username_user],
        primary_owner=employee,
    )
    add_task_comment(
        actor=employee,
        task=task,
        body="يرجى المراجعة @مراجع_عربي",
    )
    assert (
        Notification.objects.filter(
            recipient=arabic_username_user,
            message_code="mentioned",
        ).count()
        == 1
    )

    assert generate_task_deadline_notifications(today=date(2026, 8, 19)) == 2
    assert generate_task_deadline_notifications(today=date(2026, 8, 19)) == 0
    assert generate_task_deadline_notifications(today=date(2026, 8, 21)) == 2
    assert generate_task_deadline_notifications(today=date(2026, 8, 21)) == 0
    assert set(
        Notification.objects.filter(
            recipient=employee,
            category=Notification.Category.DEADLINE,
        ).values_list("message_code", flat=True)
    ) == {"task_due", "task_overdue"}


@pytest.mark.integration
@pytest.mark.django_db
def test_completion_and_attendance_notify_only_current_decision_actors() -> None:
    department = Department.objects.create(
        code="NTF11",
        name_ar="إدارة الإشعارات",
        name_en="Notifications",
    )
    manager = role_user("phase11-approval-manager", "project_manager", department)
    supervisor = role_user("phase11-approval-supervisor", "supervisor", department)
    employee = role_user("phase11-approval-employee", "employee", department)
    project = make_project(
        code="PRJ-N12",
        department=department,
        manager=manager,
        supervisor=supervisor,
    )
    ProjectMembership.objects.create(
        project=project,
        user=employee,
        added_by=manager,
    )
    task = make_task(
        code="TSK-N12",
        project=project,
        actor=manager,
        assignee=employee,
    )
    approval_request = submit_completion(actor=employee, target=task)
    assert approval_request.status == ApprovalRequest.Status.PENDING_SUPERVISOR
    assert (
        Notification.objects.filter(
            recipient=supervisor,
            message_code="approval_action",
        ).count()
        == 1
    )
    approve_request(actor=supervisor, approval_request=approval_request)
    assert (
        Notification.objects.filter(
            recipient=manager,
            message_code="approval_action",
        ).count()
        == 1
    )
    approve_request(actor=manager, approval_request=approval_request)
    assert (
        Notification.objects.filter(
            recipient=employee,
            message_code="approval_updated",
        ).count()
        == 1
    )

    attendance_manager, attendance_supervisor, submission, _link, _token = (
        create_submission()
    )
    assert Notification.objects.filter(
        recipient=attendance_supervisor,
        event_key__startswith="attendance-review:",
        message_code="approval_action",
    ).exists()
    review_attendance(
        actor=attendance_supervisor,
        submission=submission,
        decision=AttendanceReview.Decision.APPROVED,
    )
    assert Notification.objects.filter(
        recipient=attendance_manager,
        event_key__startswith="attendance-review:",
        message_code="approval_updated",
    ).exists()
