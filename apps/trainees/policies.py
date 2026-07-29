"""Approved Phase 8 import boundaries and header aliases."""

from typing import Final

MAX_IMPORT_SIZE: Final = 5 * 1024 * 1024
MAX_IMPORT_ROWS: Final = 5_000
IMPORT_MIME_TYPES: Final[dict[str, set[str]]] = {
    ".csv": {"text/csv", "application/csv", "application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}
HEADER_ALIASES: Final[dict[str, str]] = {
    "full_name": "full_name",
    "name": "full_name",
    "الاسم الكامل": "full_name",
    "الاسم": "full_name",
    "phone": "phone",
    "mobile": "phone",
    "رقم الجوال": "phone",
    "الجوال": "phone",
    "email": "email",
    "email_address": "email",
    "البريد الإلكتروني": "email",
}
REQUIRED_HEADERS: Final = frozenset({"full_name", "phone"})
OPTIONAL_HEADERS: Final = frozenset({"email"})
