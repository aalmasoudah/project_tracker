"""Phase 10 attendance review policy boundaries."""

from apps.attendance.models import AttendanceEntry, AttendanceReview
from apps.attendance.policies import (
    MAX_DECISION_REASON_LENGTH,
    REJECTION_LINK_HOURS,
)


def test_phase10_review_constants_and_stable_values() -> None:
    assert REJECTION_LINK_HOURS == 72
    assert MAX_DECISION_REASON_LENGTH == 1000
    assert AttendanceReview.Decision.values == ["approved", "rejected"]
    assert AttendanceEntry.Value.values == ["present", "absent", "late", "excused"]
