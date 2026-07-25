"""Typed environment loader for settings modules."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def load_environment_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overriding process variables."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"Invalid environment line in {path.name}.")
        normalized_value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), normalized_value)


def env_string(name: str, *, default: str = "") -> str:
    """Return a string environment value."""
    return os.environ.get(name, default)


def env_list(name: str, *, default: list[str] | None = None) -> list[str]:
    """Return a comma-separated environment value as a clean list."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def env_bool(name: str, *, default: bool = False) -> bool:
    """Return a strict boolean environment value."""
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def env_int(name: str, *, default: int = 0) -> int:
    """Return an integer environment value."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error


settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
if settings_module.endswith((".development", ".testing")):
    load_environment_file(BASE_DIR / ".env")
