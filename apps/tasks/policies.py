"""Stable Phase 5 lifecycle and file policy."""

from typing import Final

TASK_STATUS_TRANSITIONS: Final[dict[str, tuple[str, ...]]] = {
    "todo": ("in_progress", "cancelled"),
    "in_progress": ("blocked", "completed", "cancelled"),
    "blocked": ("in_progress", "cancelled"),
    "completed": ("in_progress",),
    "cancelled": ("todo",),
}
MAX_TASK_DEPTH: Final = 3
MAX_TASK_FILE_SIZE: Final = 25 * 1024 * 1024
TASK_FILE_TYPES: Final[dict[str, str]] = {
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
