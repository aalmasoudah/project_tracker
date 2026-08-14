"""Human-readable, permission-safe Phase 17 proposal presentation."""

import json
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from apps.accounts.models import User
from apps.organizations.models import Department
from apps.project_agents.models import AgentProposal, AgentRun, AgentStep
from apps.project_agents.presentation import present_agent_proposal
from apps.project_agents.schemas import empty_payload
from apps.projects.models import Project
from apps.tasks.models import Task, TaskAssignment

PASSWORD = "fictional-presentation-password-3187"


def _proposal(
    *,
    run: AgentRun,
    sequence: int,
    action_code: str,
    payload: dict[str, object],
    before_state: dict[str, object],
) -> AgentProposal:
    step = AgentStep.objects.create(
        run=run,
        sequence=sequence,
        step_type=AgentStep.StepType.PROPOSAL,
        data={
            "summary": f"Safe proposal summary {sequence}",
            "action_code": action_code,
        },
        status=AgentStep.Status.COMPLETED,
    )
    return AgentProposal.objects.create(
        run=run,
        step=step,
        action_code=action_code,
        payload=payload,
        citations=[],
        before_state=before_state,
        before_state_fingerprint=f"{sequence:064x}",
        risk=AgentProposal.Risk.LOW,
        execution_idempotency_key=f"{sequence + 10:064x}",
    )


@pytest.fixture
def presentation_proposals(db: object) -> tuple[User, AgentRun, list[AgentProposal]]:
    del db
    department = Department.objects.create(
        code="AG17-PRESENT",
        name_ar="إدارة عرض الوكيل",
        name_en="Agent presentation",
    )
    reviewer = User.objects.create_superuser(
        username="agent-presentation-reviewer",
        email="agent-presentation-reviewer@example.test",
        display_name="مراجع المقترح",
        department=department,
        preferred_language=User.Language.ARABIC,
        password=PASSWORD,
    )
    worker = User.objects.create_user(
        username="agent-presentation-worker",
        email="agent-presentation-worker@example.test",
        display_name="عضو فريق المشروع",
        department=department,
        password=PASSWORD,
    )
    project = Project.objects.create(
        code="AG17-PRESENT",
        name_ar="مشروع العرض الآمن",
        name_en="Safe presentation project",
        department=department,
        manager=reviewer,
        status=Project.Status.ACTIVE,
        priority=Project.Priority.HIGH,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by=reviewer,
        updated_by=reviewer,
    )
    task = Task.objects.create(
        code="AG17-PRESENT-TASK",
        project=project,
        name_ar="مهمة العرض",
        name_en="Presentation task",
        status=Task.Status.BLOCKED,
        priority=Task.Priority.CRITICAL,
        start_date=date(2026, 1, 1),
        due_date=date(2026, 9, 1),
        blocking_reason="اعتماد خارجي",
        created_by=reviewer,
        updated_by=reviewer,
    )
    TaskAssignment.objects.create(
        task=task,
        user=worker,
        is_primary=True,
        assigned_by=reviewer,
    )
    run = AgentRun.objects.create(
        project=project,
        requester=reviewer,
        goal_code=AgentRun.Goal.PROJECT_RECOVERY,
        language=AgentRun.Language.ARABIC,
        model_code="openai/gpt-oss-120b",
        status=AgentRun.Status.AWAITING_APPROVAL,
        current_step=5,
        input_fingerprint="a" * 64,
    )
    task_before: dict[str, object] = {
        "type": "task",
        "id": task.pk,
        "code": task.code,
        "status": task.status,
        "actual_hours": None,
        "blocking_reason": task.blocking_reason,
        "due_date": "2026-09-01",
        "assignments": [{"user_id": worker.pk, "is_primary": True}],
        "comment_count": 0,
        "updated_at": task.updated_at.isoformat(),
    }
    payloads = []
    update_payload = empty_payload()
    update_payload.update(
        status=Task.Status.IN_PROGRESS,
        actual_hours=5,
        blocking_reason="",
        task_id=task.pk,
    )
    payloads.append((AgentProposal.Action.TASK_UPDATE, update_payload, task_before))
    assignment_payload = empty_payload()
    assignment_payload.update(
        task_id=task.pk,
        assignee_ids=[reviewer.pk, worker.pk],
        primary_owner_id=worker.pk,
    )
    payloads.append(
        (AgentProposal.Action.TASK_ASSIGNMENT, assignment_payload, task_before)
    )
    comment_payload = empty_payload()
    comment_payload.update(task_id=task.pk, comment="Follow up with the dependency.")
    payloads.append((AgentProposal.Action.TASK_COMMENT, comment_payload, task_before))
    deadline_payload = empty_payload()
    deadline_payload.update(task_id=task.pk, due_date="2026-09-15")
    payloads.append(
        (AgentProposal.Action.DEADLINE_CHANGE, deadline_payload, task_before)
    )
    notification_payload = empty_payload()
    notification_payload.update(notification_topic="Project Status Update")
    team_before: dict[str, object] = {
        "type": "project_team",
        "id": project.pk,
        "member_ids": [reviewer.pk, worker.pk],
        "status": project.status,
        "archived": False,
        "updated_at": project.updated_at.isoformat(),
    }
    payloads.append(
        (
            AgentProposal.Action.TEAM_NOTIFICATION,
            notification_payload,
            team_before,
        )
    )
    proposals = [
        _proposal(
            run=run,
            sequence=index,
            action_code=action,
            payload=payload,
            before_state=before,
        )
        for index, (action, payload, before) in enumerate(payloads, start=1)
    ]
    return reviewer, run, proposals


@pytest.mark.integration
@pytest.mark.django_db
def test_all_proposal_types_present_only_relevant_human_readable_fields(
    presentation_proposals: tuple[User, AgentRun, list[AgentProposal]],
) -> None:
    reviewer, _run, proposals = presentation_proposals
    with translation.override("en"):
        presented = [present_agent_proposal(reviewer, item) for item in proposals]

    serialized = json.dumps(presented, ensure_ascii=False)
    assert "propose_" not in serialized
    assert "member_ids" not in serialized
    assert "primary_owner_id" not in serialized
    assert "None" not in serialized
    assert "AG17-PRESENT-TASK — Presentation task" in serialized
    assert "مراجع المقترح" in serialized
    assert "عضو فريق المشروع" in serialized
    assert [item["action_label"] for item in presented] == [
        "Task update",
        "Task assignment",
        "Task comment",
        "Deadline change",
        "Team notification",
    ]
    assert [field["label"] for field in presented[-1]["change_fields"]] == [
        "Notification topic"
    ]


@pytest.mark.integration
@pytest.mark.django_db
def test_arabic_approval_page_replaces_raw_payload_with_localized_fields(
    presentation_proposals: tuple[User, AgentRun, list[AgentProposal]],
) -> None:
    reviewer, run, _proposals = presentation_proposals
    client = Client()
    client.force_login(reviewer)
    response = client.get(reverse("project_agents:detail", args=(run.pk,)))

    assert response.status_code == 200
    content = response.content.decode()
    assert "إشعار الفريق" in content
    assert "موضوع الإشعار" in content
    assert "عضو فريق المشروع" in content
    assert "{'status':" not in content
    assert "'member_ids'" not in content
    assert "'notification_topic'" not in content
    assert "<pre" not in content.split("card border-warning", 1)[1]
