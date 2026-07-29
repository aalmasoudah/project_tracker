"""Non-destructive trainee duplicate keys."""

import re
import unicodedata

from apps.accounts.normalization import normalize_account_search

NON_DIGITS = re.compile(r"\D+")


def normalize_trainee_name(value: str) -> str:
    return normalize_account_search(value)


def normalize_trainee_phone(value: str) -> str:
    """Canonicalize Saudi local forms while preserving other digit sequences."""
    raw = unicodedata.normalize("NFKC", value.strip())
    digits = NON_DIGITS.sub("", raw)
    if digits.startswith("00966"):
        digits = digits[2:]
    if digits.startswith("05") and len(digits) == 10:
        digits = f"966{digits[1:]}"
    if len(digits) < 7 or len(digits) > 15:
        return ""
    return digits


def trainee_identity_key(full_name: str, phone: str) -> str:
    return f"{normalize_trainee_name(full_name)}|{normalize_trainee_phone(phone)}"
