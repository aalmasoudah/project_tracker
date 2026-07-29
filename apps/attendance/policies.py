"""Approved Phase 9 session, link, and evidence boundaries."""

from typing import Final

DEFAULT_LINK_HOURS: Final = 72
MIN_LINK_HOURS: Final = 1
MAX_LINK_HOURS: Final = 14 * 24
MAX_RECURRENCE_COUNT: Final = 52
MAX_EVIDENCE_FILES: Final = 5
MAX_EVIDENCE_SIZE: Final = 10 * 1024 * 1024
EVIDENCE_TYPES: Final[dict[str, str]] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
