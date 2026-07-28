"""Pure calculation tests for the Phase 6 progress engine."""

from decimal import Decimal

import pytest

from apps.progress.calculations import (
    ProgressCalculationError,
    ProgressResult,
    ProgressState,
    TaskProgressInput,
    TaskProgressTree,
)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("todo", Decimal("0.00")),
        ("in_progress", Decimal("0.00")),
        ("blocked", Decimal("0.00")),
        ("completed", Decimal("100.00")),
    ],
)
def test_leaf_task_progress_is_status_based(status: str, expected: Decimal) -> None:
    result = TaskProgressTree((TaskProgressInput(1, None, status),)).root_result()

    assert result.state == ProgressState.VALUE
    assert result.percentage == expected


def test_nested_progress_averages_direct_countable_children_recursively() -> None:
    tree = TaskProgressTree(
        (
            TaskProgressInput(1, None, "completed"),
            TaskProgressInput(2, 1, "completed"),
            TaskProgressInput(3, 1, "todo"),
            TaskProgressInput(4, 3, "completed"),
            TaskProgressInput(5, 3, "todo"),
        )
    )

    assert tree.result_for(3).percentage == Decimal("50.00")
    assert tree.result_for(1).percentage == Decimal("75.00")
    assert tree.root_result().percentage == Decimal("75.00")


def test_cancelled_or_archived_branches_are_excluded() -> None:
    tree = TaskProgressTree(
        (
            TaskProgressInput(1, None, "todo"),
            TaskProgressInput(2, 1, "cancelled"),
            TaskProgressInput(3, 2, "completed"),
            TaskProgressInput(4, 1, "completed", is_archived=True),
        )
    )

    # With no countable children, the active parent's own status applies.
    assert tree.result_for(1).percentage == Decimal("0.00")
    assert tree.result_for(2).state == ProgressState.EXCLUDED


def test_empty_and_rounding_states_are_explicit() -> None:
    empty = TaskProgressTree(
        (
            TaskProgressInput(1, None, "cancelled"),
            TaskProgressInput(2, None, "completed", is_archived=True),
        )
    ).root_result()
    one_third = TaskProgressTree(
        (
            TaskProgressInput(1, None, "completed"),
            TaskProgressInput(2, None, "todo"),
            TaskProgressInput(3, None, "blocked"),
        )
    ).root_result()
    two_thirds = TaskProgressTree(
        (
            TaskProgressInput(1, None, "completed"),
            TaskProgressInput(2, None, "completed"),
            TaskProgressInput(3, None, "todo"),
        )
    ).root_result()

    assert empty.state == ProgressState.EMPTY
    assert empty.percentage == Decimal("0.00")
    assert empty.excluded_items == 2
    assert one_third.percentage == Decimal("33.33")
    assert two_thirds.percentage == Decimal("66.67")


def test_public_percentage_is_bounded_and_duplicate_or_cyclic_input_fails() -> None:
    assert ProgressResult(Decimal("-1"), ProgressState.VALUE).percentage == Decimal(
        "0.00"
    )
    assert ProgressResult(Decimal("101"), ProgressState.VALUE).percentage == Decimal(
        "100.00"
    )

    with pytest.raises(ProgressCalculationError, match="unique"):
        TaskProgressTree(
            (
                TaskProgressInput(1, None, "todo"),
                TaskProgressInput(1, None, "completed"),
            )
        )

    cyclic = TaskProgressTree(
        (
            TaskProgressInput(1, 2, "todo"),
            TaskProgressInput(2, 1, "completed"),
        )
    )
    with pytest.raises(ProgressCalculationError, match="cycle"):
        cyclic.result_for(1)
