"""Stable Phase 4 lifecycle and file policy definitions."""

from typing import Final

COURSE_STATUS_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "draft": ("active", "cancelled"),
    "active": ("on_hold", "cancelled"),
    "on_hold": ("active", "cancelled"),
    "cancelled": ("draft",),
    "completed": (),
}

MAX_COURSE_FILE_SIZE: Final = 25 * 1024 * 1024
COURSE_FILE_TYPES: Final[dict[str, str]] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
