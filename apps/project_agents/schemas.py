"""Strict Phase 17 provider-decision and proposal validation."""

from decimal import Decimal, InvalidOperation
from typing import Final, TypedDict, cast

from django.utils.dateparse import parse_date

READ_TOOLS: Final = frozenset(
    {
        "get_project_snapshot",
        "list_overdue_and_blocked_tasks",
        "get_upcoming_milestones",
        "get_pending_approvals",
        "get_team_workload",
        "calculate_project_progress",
        "recall_reviewed_agent_runs",
    }
)
PROPOSAL_ACTIONS: Final = frozenset(
    {
        "propose_task_update",
        "propose_task_assignment",
        "propose_task_comment",
        "propose_deadline_change",
        "propose_team_notification",
    }
)
DECISION_KEYS: Final = {
    "kind",
    "summary",
    "plan_steps",
    "tool_code",
    "arguments",
    "action_code",
    "payload",
    "citations",
    "findings",
    "recommendations",
}
PAYLOAD_KEYS: Final = {
    "task_id",
    "status",
    "actual_hours",
    "blocking_reason",
    "assignee_ids",
    "primary_owner_id",
    "comment",
    "due_date",
    "notification_topic",
}
MAX_TEXT = 2_000
MAX_ITEMS = 10
MAX_CITATIONS = 5


class CitedText(TypedDict):
    text: str
    citations: list[str]


class AgentDecision(TypedDict):
    kind: str
    summary: str
    plan_steps: list[str]
    tool_code: str | None
    arguments: dict[str, object]
    action_code: str | None
    payload: dict[str, object]
    citations: list[str]
    findings: list[CitedText]
    recommendations: list[CitedText]


class AgentSchemaError(ValueError):
    """Raised when provider-controlled structured data is not safe."""


def _text(value: object, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise AgentSchemaError(f"{field} must be text.")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise AgentSchemaError(f"{field} cannot be empty.")
    if len(cleaned) > MAX_TEXT:
        raise AgentSchemaError(f"{field} is too long.")
    return cleaned


def _string_list(value: object, field: str, *, maximum: int = MAX_ITEMS) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise AgentSchemaError(f"{field} must be a bounded list.")
    return [_text(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _citations(value: object, allowed: frozenset[str]) -> list[str]:
    citations = _string_list(value, "citations", maximum=MAX_CITATIONS)
    if any(item not in allowed for item in citations):
        raise AgentSchemaError("A citation was not observed in this run.")
    return list(dict.fromkeys(citations))


def _cited_items(value: object, allowed: frozenset[str], field: str) -> list[CitedText]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise AgentSchemaError(f"{field} must be a bounded list.")
    result: list[CitedText] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"text", "citations"}:
            raise AgentSchemaError(f"{field}[{index}] has invalid fields.")
        citations = _citations(item["citations"], allowed)
        if not citations:
            raise AgentSchemaError(f"{field}[{index}] requires a citation.")
        result.append(
            {
                "text": _text(item["text"], f"{field}[{index}].text"),
                "citations": citations,
            }
        )
    return result


def empty_payload() -> dict[str, object]:
    return {
        "task_id": None,
        "status": None,
        "actual_hours": None,
        "blocking_reason": "",
        "assignee_ids": [],
        "primary_owner_id": None,
        "comment": "",
        "due_date": "",
        "notification_topic": "",
    }


def validate_decision(
    value: object,
    *,
    allowed_citations: frozenset[str],
) -> AgentDecision:
    if not isinstance(value, dict) or set(value) != DECISION_KEYS:
        raise AgentSchemaError("Agent decision fields are invalid.")
    kind = _text(value["kind"], "kind")
    if kind not in {"plan", "tool_call", "proposal", "final"}:
        raise AgentSchemaError("Agent decision kind is invalid.")
    tool_code = value["tool_code"]
    if tool_code is not None and tool_code not in READ_TOOLS:
        raise AgentSchemaError("Agent tool is not allowlisted.")
    action_code = value["action_code"]
    if action_code is not None and action_code not in PROPOSAL_ACTIONS:
        raise AgentSchemaError("Agent proposal action is not allowlisted.")
    arguments = value["arguments"]
    if not isinstance(arguments, dict) or arguments:
        raise AgentSchemaError("Read tools accept no provider-controlled arguments.")
    payload = value["payload"]
    if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS:
        raise AgentSchemaError("Proposal payload fields are invalid.")
    normalized: AgentDecision = {
        "kind": kind,
        "summary": _text(value["summary"], "summary", allow_empty=kind == "tool_call"),
        "plan_steps": _string_list(value["plan_steps"], "plan_steps"),
        "tool_code": cast(str | None, tool_code),
        "arguments": {},
        "action_code": cast(str | None, action_code),
        "payload": cast(dict[str, object], payload),
        "citations": _citations(value["citations"], allowed_citations),
        "findings": _cited_items(value["findings"], allowed_citations, "findings"),
        "recommendations": _cited_items(
            value["recommendations"], allowed_citations, "recommendations"
        ),
    }
    if kind == "plan":
        if not 2 <= len(normalized["plan_steps"]) <= 6:
            raise AgentSchemaError("A plan requires two to six steps.")
        if tool_code is not None or action_code is not None:
            raise AgentSchemaError("A plan cannot call a tool or proposal.")
    elif kind == "tool_call":
        if tool_code is None or action_code is not None:
            raise AgentSchemaError("A tool decision requires one read tool.")
    elif kind == "proposal":
        if action_code is None or tool_code is not None:
            raise AgentSchemaError("A proposal decision requires one action.")
        if not normalized["citations"]:
            raise AgentSchemaError("A proposal requires observed citations.")
        if not normalized["findings"] or not normalized["recommendations"]:
            raise AgentSchemaError(
                "A proposal requires cited findings and recommendations."
            )
    elif tool_code is not None or action_code is not None:
        raise AgentSchemaError("A final decision cannot call a tool or action.")
    return normalized


def validate_proposal_payload(
    action_code: str,
    payload: dict[str, object],
    *,
    observed_task_ids: frozenset[int],
    observed_user_ids: frozenset[int],
) -> dict[str, object]:
    if set(payload) != PAYLOAD_KEYS:
        raise AgentSchemaError("Proposal payload fields are invalid.")
    task_id = payload["task_id"]
    if action_code != "propose_team_notification":
        if not isinstance(task_id, int) or isinstance(task_id, bool):
            raise AgentSchemaError("A proposal requires an observed task.")
        if task_id not in observed_task_ids:
            raise AgentSchemaError("The task identifier was not observed.")
    result = empty_payload()
    result["task_id"] = task_id
    if action_code == "propose_task_update":
        status = payload["status"]
        if status not in {"todo", "in_progress", "blocked"}:
            raise AgentSchemaError("The proposed task status is not allowed.")
        result["status"] = status
        raw_hours = payload["actual_hours"]
        if raw_hours is not None:
            try:
                hours = Decimal(str(raw_hours))
            except InvalidOperation as error:
                raise AgentSchemaError("Actual hours are invalid.") from error
            if hours < 0 or hours > Decimal("9999999.99"):
                raise AgentSchemaError("Actual hours are outside the allowed range.")
            result["actual_hours"] = str(hours.quantize(Decimal("0.01")))
        reason = _text(payload["blocking_reason"], "blocking_reason", allow_empty=True)
        if status == "blocked" and not reason:
            raise AgentSchemaError("A blocked task requires a reason.")
        result["blocking_reason"] = reason
    elif action_code == "propose_task_assignment":
        ids = payload["assignee_ids"]
        primary = payload["primary_owner_id"]
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 20
            or any(not isinstance(item, int) or isinstance(item, bool) for item in ids)
        ):
            raise AgentSchemaError("Assignee identifiers are invalid.")
        unique_ids = list(dict.fromkeys(cast(list[int], ids)))
        if any(item not in observed_user_ids for item in unique_ids):
            raise AgentSchemaError("An assignee identifier was not observed.")
        if not isinstance(primary, int) or primary not in unique_ids:
            raise AgentSchemaError("Primary owner must be an observed assignee.")
        result["assignee_ids"] = unique_ids
        result["primary_owner_id"] = primary
    elif action_code == "propose_task_comment":
        result["comment"] = _text(payload["comment"], "comment")[:2_000]
    elif action_code == "propose_deadline_change":
        due_date = _text(payload["due_date"], "due_date")
        if parse_date(due_date) is None:
            raise AgentSchemaError("The proposed due date is invalid.")
        result["due_date"] = due_date
    elif action_code == "propose_team_notification":
        result["task_id"] = None
        result["notification_topic"] = _text(
            payload["notification_topic"], "notification_topic"
        )[:200]
    else:
        raise AgentSchemaError("The proposal action is not allowlisted.")
    return result


def agent_decision_json_schema(
    *,
    allowed_citations: frozenset[str] | None = None,
    stage: str | None = None,
    available_tools: frozenset[str] | None = None,
    available_actions: frozenset[str] | None = None,
    observed_task_ids: frozenset[int] | None = None,
    observed_user_ids: frozenset[int] | None = None,
) -> dict[str, object]:
    citation_items: dict[str, object] = {"type": "string"}
    if allowed_citations:
        citation_items["enum"] = sorted(allowed_citations)
    citation_list: dict[str, object] = {
        "type": "array",
        "items": citation_items,
        "maxItems": MAX_CITATIONS,
    }
    if allowed_citations == frozenset():
        citation_list["maxItems"] = 0
    if stage == "proposal":
        citation_list["minItems"] = 1
    cited = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "maxLength": MAX_TEXT},
            "citations": citation_list,
        },
        "required": ["text", "citations"],
        "additionalProperties": False,
    }
    task_id_schema: dict[str, object] = {"type": ["integer", "null"]}
    if observed_task_ids is not None:
        task_id_schema["enum"] = [None, *sorted(observed_task_ids)]
    user_id_schema: dict[str, object] = {"type": "integer"}
    primary_owner_schema: dict[str, object] = {"type": ["integer", "null"]}
    if observed_user_ids is not None:
        user_id_schema["enum"] = sorted(observed_user_ids)
        primary_owner_schema["enum"] = [None, *sorted(observed_user_ids)]
    payload_properties: dict[str, object] = {
        "task_id": task_id_schema,
        "status": {
            "type": ["string", "null"],
            "enum": [None, "todo", "in_progress", "blocked"],
        },
        "actual_hours": {"type": ["number", "null"], "minimum": 0},
        "blocking_reason": {"type": "string", "maxLength": MAX_TEXT},
        "assignee_ids": {
            "type": "array",
            "items": user_id_schema,
            "maxItems": 20,
        },
        "primary_owner_id": primary_owner_schema,
        "comment": {"type": "string", "maxLength": MAX_TEXT},
        "due_date": {"type": "string", "maxLength": 10},
        "notification_topic": {"type": "string", "maxLength": 200},
    }
    kind_values = (
        [stage]
        if stage in {"plan", "tool_call", "proposal", "final"}
        else ["plan", "tool_call", "proposal", "final"]
    )
    plan_steps_schema: dict[str, object] = {
        "type": "array",
        "items": {"type": "string", "maxLength": MAX_TEXT},
        "maxItems": 6,
    }
    if stage == "plan":
        plan_steps_schema["minItems"] = 2
    elif stage is not None:
        plan_steps_schema["maxItems"] = 0
    tool_values: list[str | None] = [None, *sorted(READ_TOOLS)]
    if stage == "tool_call":
        tool_values = cast(list[str | None], sorted(available_tools or READ_TOOLS))
    elif stage is not None:
        tool_values = [None]
    action_values: list[str | None] = [None, *sorted(PROPOSAL_ACTIONS)]
    if stage == "proposal":
        action_values = cast(
            list[str | None], sorted(available_actions or PROPOSAL_ACTIONS)
        )
    elif stage is not None:
        action_values = [None]
    cited_max_items = 0 if stage in {"plan", "tool_call"} else MAX_ITEMS
    cited_min_items = 1 if stage == "proposal" else 0
    return {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": kind_values,
            },
            "summary": {"type": "string", "maxLength": MAX_TEXT},
            "plan_steps": plan_steps_schema,
            "tool_code": {
                "type": ["string", "null"],
                "enum": tool_values,
            },
            "arguments": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "action_code": {
                "type": ["string", "null"],
                "enum": action_values,
            },
            "payload": {
                "type": "object",
                "properties": payload_properties,
                "required": sorted(PAYLOAD_KEYS),
                "additionalProperties": False,
            },
            "citations": citation_list,
            "findings": {
                "type": "array",
                "items": cited,
                "minItems": cited_min_items,
                "maxItems": cited_max_items,
            },
            "recommendations": {
                "type": "array",
                "items": cited,
                "minItems": cited_min_items,
                "maxItems": cited_max_items,
            },
        },
        "required": sorted(DECISION_KEYS),
        "additionalProperties": False,
    }
