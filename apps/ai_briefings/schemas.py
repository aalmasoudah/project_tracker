"""Strict provider output schema and local validation."""

from typing import Final, TypedDict, cast


class CitedItem(TypedDict):
    text: str
    citations: list[str]


class RiskItem(CitedItem):
    severity: str


class BriefingOutput(TypedDict):
    summary: str
    highlights: list[CitedItem]
    risks: list[RiskItem]
    upcoming: list[CitedItem]
    recommended_actions: list[CitedItem]
    data_gaps: list[str]


OUTPUT_KEYS: Final = {
    "summary",
    "highlights",
    "risks",
    "upcoming",
    "recommended_actions",
    "data_gaps",
}
SEVERITIES: Final = {"low", "medium", "high", "critical"}
MAX_SECTION_ITEMS: Final = 10
MAX_TEXT_LENGTH: Final = 2_000
MAX_CITATIONS_PER_ITEM: Final = 5


class BriefingValidationError(ValueError):
    """Raised when a provider result is unsafe or violates the contract."""


def _string(value: object, *, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise BriefingValidationError(f"{field} must be a string.")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise BriefingValidationError(f"{field} cannot be empty.")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise BriefingValidationError(f"{field} is too long.")
    return cleaned


def _citations(value: object, *, field: str, allowed: frozenset[str]) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_CITATIONS_PER_ITEM:
        raise BriefingValidationError(f"{field} must contain valid citations.")
    citations: list[str] = []
    for index, item in enumerate(value):
        citation = _string(item, field=f"{field}[{index}]")
        if citation not in allowed:
            raise BriefingValidationError(f"{field} contains an unknown citation.")
        if citation not in citations:
            citations.append(citation)
    return citations


def _cited_items(
    value: object,
    *,
    field: str,
    allowed: frozenset[str],
    risks: bool = False,
) -> list[CitedItem] | list[RiskItem]:
    if not isinstance(value, list) or len(value) > MAX_SECTION_ITEMS:
        raise BriefingValidationError(f"{field} must be a bounded list.")
    cited_result: list[CitedItem] = []
    risk_result: list[RiskItem] = []
    expected_keys = (
        {"text", "citations", "severity"}
        if risks
        else {
            "text",
            "citations",
        }
    )
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != expected_keys:
            raise BriefingValidationError(f"{field}[{index}] has invalid fields.")
        common: CitedItem = {
            "text": _string(item["text"], field=f"{field}[{index}].text"),
            "citations": _citations(
                item["citations"],
                field=f"{field}[{index}].citations",
                allowed=allowed,
            ),
        }
        if risks:
            severity = _string(
                item["severity"],
                field=f"{field}[{index}].severity",
            )
            if severity not in SEVERITIES:
                raise BriefingValidationError("Risk severity is invalid.")
            risk_result.append(RiskItem(**common, severity=severity))
        else:
            cited_result.append(common)
    return risk_result if risks else cited_result


def validate_briefing_output(
    value: object,
    *,
    allowed_citations: frozenset[str],
) -> BriefingOutput:
    """Return a normalized result only when schema and citations are valid."""
    if not isinstance(value, dict) or set(value) != OUTPUT_KEYS:
        raise BriefingValidationError("Briefing output fields are invalid.")
    gaps_value = value["data_gaps"]
    if not isinstance(gaps_value, list) or len(gaps_value) > MAX_SECTION_ITEMS:
        raise BriefingValidationError("data_gaps must be a bounded list.")
    gaps = [
        _string(item, field=f"data_gaps[{index}]")
        for index, item in enumerate(gaps_value)
    ]
    return {
        "summary": _string(value["summary"], field="summary"),
        "highlights": cast(
            list[CitedItem],
            _cited_items(
                value["highlights"],
                field="highlights",
                allowed=allowed_citations,
            ),
        ),
        "risks": cast(
            list[RiskItem],
            _cited_items(
                value["risks"],
                field="risks",
                allowed=allowed_citations,
                risks=True,
            ),
        ),
        "upcoming": cast(
            list[CitedItem],
            _cited_items(
                value["upcoming"],
                field="upcoming",
                allowed=allowed_citations,
            ),
        ),
        "recommended_actions": cast(
            list[CitedItem],
            _cited_items(
                value["recommended_actions"],
                field="recommended_actions",
                allowed=allowed_citations,
            ),
        ),
        "data_gaps": gaps,
    }


def briefing_json_schema() -> dict[str, object]:
    """Return the strict JSON Schema accepted by both approved Groq models."""
    cited_item: dict[str, object] = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "maxLength": MAX_TEXT_LENGTH},
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": MAX_CITATIONS_PER_ITEM,
            },
        },
        "required": ["text", "citations"],
        "additionalProperties": False,
    }
    risk_item: dict[str, object] = {
        "type": "object",
        "properties": {
            **cast(dict[str, object], cited_item["properties"]),
            "severity": {
                "type": "string",
                "enum": sorted(SEVERITIES),
            },
        },
        "required": ["text", "citations", "severity"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "maxLength": MAX_TEXT_LENGTH},
            "highlights": {
                "type": "array",
                "items": cited_item,
                "maxItems": MAX_SECTION_ITEMS,
            },
            "risks": {
                "type": "array",
                "items": risk_item,
                "maxItems": MAX_SECTION_ITEMS,
            },
            "upcoming": {
                "type": "array",
                "items": cited_item,
                "maxItems": MAX_SECTION_ITEMS,
            },
            "recommended_actions": {
                "type": "array",
                "items": cited_item,
                "maxItems": MAX_SECTION_ITEMS,
            },
            "data_gaps": {
                "type": "array",
                "items": {"type": "string", "maxLength": MAX_TEXT_LENGTH},
                "maxItems": MAX_SECTION_ITEMS,
            },
        },
        "required": sorted(OUTPUT_KEYS),
        "additionalProperties": False,
    }
