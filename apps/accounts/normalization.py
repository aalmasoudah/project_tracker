"""Approved account identity and Arabic search normalization."""

import re
import unicodedata

ARABIC_DIACRITICS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
ARABIC_SEARCH_TRANSLATION = str.maketrans(
    {
        "آ": "\u0627",
        "أ": "\u0627",
        "إ": "\u0627",
        "ٱ": "\u0627",
        "ک": "ك",
        "ی": "ي",
    }
)


def normalize_username(value: str) -> str:
    """Normalize username compatibility and surrounding whitespace."""
    return unicodedata.normalize("NFKC", value.strip())


def normalize_email(value: str) -> str:
    """Normalize an email for approved case-insensitive identity comparison."""
    return unicodedata.normalize("NFKC", value.strip()).casefold()


def normalize_login_identifier(value: str) -> str:
    """Normalize a login identifier before hashing or comparison."""
    return normalize_username(value).casefold()


def normalize_account_search(value: str) -> str:
    """Build a non-destructive, conservative Arabic account search key."""
    normalized = unicodedata.normalize("NFKC", value.strip()).casefold()
    normalized = ARABIC_DIACRITICS.sub("", normalized)
    normalized = normalized.replace("ـ", "")
    normalized = normalized.translate(ARABIC_SEARCH_TRANSLATION)
    return " ".join(normalized.split())
