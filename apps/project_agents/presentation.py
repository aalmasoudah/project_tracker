"""Permission-safe, localized presentation for Phase 17 proposals."""

from typing import TypedDict

from django.db import models
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.accounts.selectors import users_visible_to
from apps.project_agents.models import AgentProposal
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.tasks.selectors import tasks_visible_to


class ProposalField(TypedDict):
    label: str
    value: str
    url: str


class PresentedProposal(TypedDict):
    action_label: str
    summary: str
    before_fields: list[ProposalField]
    change_fields: list[ProposalField]


def _field(label: object, value: object, *, url: str = "") -> ProposalField:
    rendered = str(value).strip() if value is not None else ""
    return {
        "label": str(label),
        "value": rendered or str(_("Not provided")),
        "url": url,
    }


def _language_code() -> str:
    return "ar" if str(get_language() or "").lower().startswith("ar") else "en"


def _choice_label(choices: type[models.TextChoices], value: object) -> str:
    try:
        return str(choices(str(value)).label)
    except ValueError:
        return str(_("Not provided"))


def _visible_task(actor: User, task_id: object) -> Task | None:
    if not isinstance(task_id, int) or isinstance(task_id, bool):
        return None
    return tasks_visible_to(actor, include_archived=True).filter(pk=task_id).first()


def _task_field(actor: User, task_id: object) -> ProposalField:
    task = _visible_task(actor, task_id)
    if task is None:
        return _field(_("Task"), None)
    label = f"{task.code} — {task.localized_name(_language_code())}"
    return _field(_("Task"), label, url=reverse("tasks:detail", args=(task.pk,)))


def _project_field(proposal: AgentProposal) -> ProposalField:
    project = proposal.run.project
    label = f"{project.code} — {project.localized_name(_language_code())}"
    return _field(
        _("Project"),
        label,
        url=reverse("projects:detail", args=(project.pk,)),
    )


def _visible_user_labels(actor: User, raw_ids: object) -> list[str]:
    if not isinstance(raw_ids, list):
        return []
    user_ids = [
        item for item in raw_ids if isinstance(item, int) and not isinstance(item, bool)
    ]
    visible = {
        user.pk: user.display_name
        for user in users_visible_to(actor).filter(pk__in=user_ids)
    }
    return [visible[user_id] for user_id in user_ids if user_id in visible]


def _assignment_ids(raw_assignments: object) -> tuple[list[int], int | None]:
    if not isinstance(raw_assignments, list):
        return [], None
    user_ids: list[int] = []
    primary_id: int | None = None
    for item in raw_assignments:
        if not isinstance(item, dict):
            continue
        user_id = item.get("user_id")
        if not isinstance(user_id, int) or isinstance(user_id, bool):
            continue
        user_ids.append(user_id)
        if item.get("is_primary") is True:
            primary_id = user_id
    return user_ids, primary_id


def _joined_names(actor: User, raw_ids: object) -> str:
    labels = _visible_user_labels(actor, raw_ids)
    return ", ".join(labels) if labels else str(_("Not provided"))


def _task_before_fields(
    actor: User,
    proposal: AgentProposal,
    *,
    include_status: bool = False,
    include_hours: bool = False,
    include_blocking: bool = False,
    include_assignments: bool = False,
    include_comments: bool = False,
    include_due_date: bool = False,
) -> list[ProposalField]:
    before = proposal.before_state if isinstance(proposal.before_state, dict) else {}
    fields = [_task_field(actor, before.get("id"))]
    if include_status:
        fields.append(
            _field(_("Status"), _choice_label(Task.Status, before.get("status")))
        )
    if include_hours:
        fields.append(_field(_("Actual hours"), before.get("actual_hours")))
    if include_blocking and before.get("blocking_reason"):
        fields.append(_field(_("Blocking reason"), before["blocking_reason"]))
    if include_assignments:
        user_ids, primary_id = _assignment_ids(before.get("assignments"))
        fields.append(_field(_("Assignees"), _joined_names(actor, user_ids)))
        primary = _visible_user_labels(actor, [primary_id] if primary_id else [])
        fields.append(_field(_("Primary owner"), primary[0] if primary else None))
    if include_comments:
        fields.append(_field(_("Comments"), before.get("comment_count", 0)))
    if include_due_date:
        fields.append(_field(_("Due date"), before.get("due_date")))
    return fields


def present_agent_proposal(actor: User, proposal: AgentProposal) -> PresentedProposal:
    """Return only human-readable, permission-scoped proposal fields."""
    payload = proposal.payload if isinstance(proposal.payload, dict) else {}
    action = proposal.action_code
    before_fields: list[ProposalField]
    change_fields: list[ProposalField]

    if action == AgentProposal.Action.TASK_UPDATE:
        before_fields = _task_before_fields(
            actor,
            proposal,
            include_status=True,
            include_hours=True,
            include_blocking=True,
        )
        change_fields = [
            _field(_("Status"), _choice_label(Task.Status, payload.get("status")))
        ]
        if payload.get("actual_hours") is not None:
            change_fields.append(_field(_("Actual hours"), payload["actual_hours"]))
        if payload.get("blocking_reason"):
            change_fields.append(
                _field(_("Blocking reason"), payload["blocking_reason"])
            )
    elif action == AgentProposal.Action.TASK_ASSIGNMENT:
        before_fields = _task_before_fields(actor, proposal, include_assignments=True)
        assignee_ids = payload.get("assignee_ids")
        change_fields = [_field(_("Assignees"), _joined_names(actor, assignee_ids))]
        primary = _visible_user_labels(
            actor,
            [payload.get("primary_owner_id")]
            if payload.get("primary_owner_id") is not None
            else [],
        )
        change_fields.append(
            _field(_("Primary owner"), primary[0] if primary else None)
        )
    elif action == AgentProposal.Action.TASK_COMMENT:
        before_fields = _task_before_fields(actor, proposal, include_comments=True)
        change_fields = [_field(_("Comment"), payload.get("comment"))]
    elif action == AgentProposal.Action.DEADLINE_CHANGE:
        before_fields = _task_before_fields(actor, proposal, include_due_date=True)
        change_fields = [_field(_("Due date"), payload.get("due_date"))]
    elif action == AgentProposal.Action.TEAM_NOTIFICATION:
        before = (
            proposal.before_state if isinstance(proposal.before_state, dict) else {}
        )
        before_fields = [
            _project_field(proposal),
            _field(_("Status"), _choice_label(Project.Status, before.get("status"))),
            _field(_("Archived"), _("Yes") if before.get("archived") else _("No")),
            _field(
                _("Team members"),
                _joined_names(actor, before.get("member_ids")),
            ),
        ]
        change_fields = [
            _field(_("Notification topic"), payload.get("notification_topic"))
        ]
    else:
        before_fields = []
        change_fields = []

    step_data = proposal.step.data if isinstance(proposal.step.data, dict) else {}
    return {
        "action_label": str(proposal.get_action_code_display()),
        "summary": str(step_data.get("summary", "")),
        "before_fields": before_fields,
        "change_fields": change_fields,
    }
