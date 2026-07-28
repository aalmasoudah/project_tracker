"""Pure Decimal-safe Phase 6 progress calculations."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

ZERO = Decimal("0")
HUNDRED = Decimal("100")
PERCENT_QUANTUM = Decimal("0.01")
COMPLETED_STATUS = "completed"
CANCELLED_STATUS = "cancelled"


class ProgressState(StrEnum):
    """Presentation-neutral result states."""

    VALUE = "value"
    EMPTY = "empty"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class ProgressResult:
    """An unrounded internal value with a stable public percentage."""

    raw_percentage: Decimal
    state: ProgressState
    included_items: int = 0
    excluded_items: int = 0

    @property
    def percentage(self) -> Decimal:
        """Return the bounded two-decimal public value."""
        bounded = min(HUNDRED, max(ZERO, self.raw_percentage))
        return bounded.quantize(PERCENT_QUANTUM, rounding=ROUND_HALF_UP)

    @classmethod
    def excluded(cls) -> "ProgressResult":
        return cls(raw_percentage=ZERO, state=ProgressState.EXCLUDED)

    @classmethod
    def empty(cls, *, excluded_items: int = 0) -> "ProgressResult":
        return cls(
            raw_percentage=ZERO,
            state=ProgressState.EMPTY,
            excluded_items=excluded_items,
        )


@dataclass(frozen=True, slots=True)
class TaskProgressInput:
    """Minimal task data required by the calculation engine."""

    task_id: int
    parent_id: int | None
    status: str
    is_archived: bool = False


class ProgressCalculationError(ValueError):
    """Raised when corrupted input cannot be calculated safely."""


def average(values: Iterable[Decimal]) -> Decimal:
    """Return an unrounded equal-weight average, or zero for no values."""
    items = tuple(values)
    if not items:
        return ZERO
    return sum(items, start=ZERO) / Decimal(len(items))


class TaskProgressTree:
    """Calculate a bounded task hierarchy entirely in memory."""

    def __init__(self, tasks: Iterable[TaskProgressInput]) -> None:
        self._tasks: dict[int, TaskProgressInput] = {}
        self._children: dict[int, list[int]] = defaultdict(list)
        for task in tasks:
            if task.task_id in self._tasks:
                raise ProgressCalculationError("Task identifiers must be unique.")
            self._tasks[task.task_id] = task
            if task.parent_id is not None:
                self._children[task.parent_id].append(task.task_id)
        self._cache: dict[int, Decimal | None] = {}

    def result_for(self, task_id: int) -> ProgressResult:
        """Return one task's recursive progress."""
        raw = self._raw_for(task_id, frozenset())
        if raw is None:
            return ProgressResult.excluded()
        return ProgressResult(
            raw_percentage=raw,
            state=ProgressState.VALUE,
            included_items=1,
        )

    def root_result(self) -> ProgressResult:
        """Average countable top-level tasks."""
        roots = (
            task.task_id for task in self._tasks.values() if task.parent_id is None
        )
        return self.result_for_ids(roots)

    def result_for_ids(self, task_ids: Iterable[int]) -> ProgressResult:
        """Average countable task roots from the supplied identifiers."""
        values: list[Decimal] = []
        excluded = 0
        for task_id in task_ids:
            raw = self._raw_for(task_id, frozenset())
            if raw is None:
                excluded += 1
            else:
                values.append(raw)
        if not values:
            return ProgressResult.empty(excluded_items=excluded)
        return ProgressResult(
            raw_percentage=average(values),
            state=ProgressState.VALUE,
            included_items=len(values),
            excluded_items=excluded,
        )

    def _raw_for(self, task_id: int, ancestors: frozenset[int]) -> Decimal | None:
        if task_id in self._cache:
            return self._cache[task_id]
        task = self._tasks.get(task_id)
        if task is None:
            raise ProgressCalculationError(f"Unknown task identifier: {task_id}")
        if task_id in ancestors:
            raise ProgressCalculationError("Task hierarchy contains a cycle.")
        if task.is_archived or task.status == CANCELLED_STATUS:
            self._cache[task_id] = None
            return None

        next_ancestors = ancestors | {task_id}
        child_values = [
            value
            for child_id in self._children.get(task_id, ())
            if (value := self._raw_for(child_id, next_ancestors)) is not None
        ]
        raw = (
            average(child_values)
            if child_values
            else HUNDRED
            if task.status == COMPLETED_STATUS
            else ZERO
        )
        self._cache[task_id] = raw
        return raw
