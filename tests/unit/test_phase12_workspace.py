"""Pure Phase 12 filter validation tests."""

from datetime import date

import pytest

from apps.workspace.forms import (
    PlanningFilterForm,
    SavedFilterForm,
    criteria_from_cleaned_data,
)


@pytest.mark.unit
def test_planning_range_is_bounded_and_ordered() -> None:
    reversed_range = PlanningFilterForm(
        {"date_from": "2026-09-02", "date_to": "2026-09-01"}
    )
    excessive_range = PlanningFilterForm(
        {"date_from": "2026-01-01", "date_to": "2026-12-31"}
    )
    assert not reversed_range.is_valid()
    assert not excessive_range.is_valid()


@pytest.mark.unit
def test_saved_filter_serializes_only_allowlisted_fields() -> None:
    form = SavedFilterForm(
        {
            "name": "August plan",
            "view_type": "gantt",
            "q": "تحول",
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "status": "forged",
            "owner": "forged",
        }
    )
    assert form.is_valid(), form.errors
    assert criteria_from_cleaned_data(form.cleaned_data) == {
        "q": "تحول",
        "date_from": date(2026, 8, 1).isoformat(),
        "date_to": date(2026, 8, 31).isoformat(),
    }


@pytest.mark.unit
def test_search_requires_two_characters() -> None:
    assert not PlanningFilterForm({"q": "a"}).is_valid()
