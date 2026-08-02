"""Permission-safe domain event to notification adapters."""

import re
from collections.abc import Iterable
from datetime import date, timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest, ApprovalStep
from apps.attendance.models import AttendanceSubmission
from apps.notifications.policies import MAX_MENTIONS_PER_COMMENT
from apps.notifications.services import create_notification
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.tasks.selectors import tasks_visible_to

MENTION_PATTERN = re.compile(r"(?<![\w@])@([\w.+-]{1,150})")


def notify_task_assignments(assignments: Iterable[TaskAssignment]) -> int:
    created = 0
    for assignment in assignments:
        if (
            create_notification(
                recipient=assignment.user,
                message_code="task_assigned",
                event_key=f"task-assignment:{assignment.pk}",
                target_path=reverse("tasks:detail", args=[assignment.task_id]),
            )
            is not None
        ):
            created += 1
    return created


def notify_task_mentions(comment: TaskComment) -> int:
    usernames = list(dict.fromkeys(MENTION_PATTERN.findall(comment.body)))
    if not usernames:
        return 0
    query = Q()
    for username in usernames[:MAX_MENTIONS_PER_COMMENT]:
        query |= Q(username__iexact=username)
    recipients = User.objects.filter(query, is_active=True).exclude(
        pk=comment.author_id
    )
    created = 0
    for recipient in recipients:
        if not tasks_visible_to(recipient).filter(pk=comment.task_id).exists():
            continue
        if (
            create_notification(
                recipient=recipient,
                message_code="mentioned",
                event_key=f"task-comment-mention:{comment.pk}:{recipient.pk}",
                target_path=reverse("tasks:detail", args=[comment.task_id]),
            )
            is not None
        ):
            created += 1
    return created


def notify_approval_action(
    approval_request: ApprovalRequest, step: ApprovalStep
) -> None:
    create_notification(
        recipient=step.approver,
        message_code="approval_action",
        event_key=f"completion-approval:{approval_request.pk}:step:{step.sequence}",
        target_path=reverse("approvals:detail", args=[approval_request.pk]),
    )


def notify_approval_updated(
    approval_request: ApprovalRequest,
    *,
    event: str,
    actor: User,
) -> None:
    if approval_request.submitted_by_id == actor.pk:
        return
    create_notification(
        recipient=approval_request.submitted_by,
        message_code="approval_updated",
        event_key=f"completion-approval:{approval_request.pk}:{event}",
        target_path=reverse("approvals:detail", args=[approval_request.pk]),
    )


def notify_attendance_review(submission: AttendanceSubmission) -> None:
    supervisor = submission.session.course.project.supervisor
    if supervisor is None:
        return
    create_notification(
        recipient=supervisor,
        message_code="approval_action",
        event_key=(
            f"attendance-review:{submission.pk}:{submission.reviews.count() + 1}"
        ),
        target_path=reverse("attendance:submission-detail", args=[submission.pk]),
    )


def notify_attendance_updated(
    submission: AttendanceSubmission,
    *,
    event: str,
    actor: User,
) -> None:
    recipient = submission.trainer_link.issued_by
    if recipient.pk == actor.pk:
        return
    create_notification(
        recipient=recipient,
        message_code="approval_updated",
        event_key=f"attendance-review:{submission.pk}:{event}:{submission.reviews.count()}",
        target_path=reverse("attendance:submission-detail", args=[submission.pk]),
    )


def generate_task_deadline_notifications(*, today: date | None = None) -> int:
    current_date = today or timezone.localdate()
    tomorrow = current_date + timedelta(days=1)
    tasks = (
        Task.objects.filter(
            is_archived=False,
            due_date__isnull=False,
        )
        .filter(
            Q(
                project__isnull=False,
                project__is_archived=False,
            )
            | Q(
                course__isnull=False,
                course__is_archived=False,
                course__project__is_archived=False,
            )
        )
        .exclude(status__in=(Task.Status.COMPLETED, Task.Status.CANCELLED))
        .exclude(project__status="cancelled")
        .exclude(course__status="cancelled")
        .exclude(course__project__status="cancelled")
        .filter(due_date__lte=tomorrow)
        .prefetch_related("assignments__user")
    )
    created = 0
    for task in tasks:
        if task.due_date is None:
            continue
        message_code = "task_due" if task.due_date == tomorrow else "task_overdue"
        event_date = task.due_date if message_code == "task_due" else current_date
        for assignment in task.assignments.all():
            if assignment.removed_at is not None or not assignment.user.is_active:
                continue
            if (
                create_notification(
                    recipient=assignment.user,
                    message_code=message_code,
                    event_key=(
                        f"task-reminder:{message_code}:{task.pk}:{event_date.isoformat()}"
                    ),
                    target_path=reverse("tasks:detail", args=[task.pk]),
                )
                is not None
            ):
                created += 1
    return created
