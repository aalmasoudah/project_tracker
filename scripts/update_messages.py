"""Update project gettext catalogs without requiring GNU gettext."""

import ast
import re
from pathlib import Path

import polib

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("apps", "config")
TEMPLATE_TRANSLATE_RE = re.compile(
    r"""{%\s*(?:translate|trans)\s+(?P<quote>["'])(?P<message>.*?)(?P=quote)"""
)


def python_messages(path: Path) -> set[str]:
    """Extract literal gettext calls from one Python module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    messages: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        function_name = function.id if isinstance(function, ast.Name) else ""
        if function_name not in {"_", "gettext", "gettext_lazy"}:
            continue
        message = node.args[0]
        if isinstance(message, ast.Constant) and isinstance(message.value, str):
            messages.add(message.value)
    return messages


def template_messages(path: Path) -> set[str]:
    """Extract literal translate tags from one Django template."""
    source = path.read_text(encoding="utf-8")
    return {match.group("message") for match in TEMPLATE_TRANSLATE_RE.finditer(source)}


def collect_messages() -> set[str]:
    """Collect project-owned messages from Python and templates."""
    messages: set[str] = set()
    for source_root in SOURCE_ROOTS:
        for path in (BASE_DIR / source_root).rglob("*.py"):
            if "migrations" not in path.parts:
                messages.update(python_messages(path))
    for path in (BASE_DIR / "templates").rglob("*.html"):
        messages.update(template_messages(path))
    return messages


def update_catalog(po_path: Path, messages: set[str]) -> None:
    """Merge extracted messages into a catalog without discarding translations."""
    catalog = polib.pofile(po_path)
    existing = {entry.msgid: entry for entry in catalog if not entry.obsolete}
    for message in sorted(messages):
        if message not in existing:
            catalog.append(polib.POEntry(msgid=message, msgstr=""))
    for entry in catalog:
        if entry.msgid and entry.msgid not in messages:
            entry.obsolete = True
    catalog.metadata["POT-Creation-Date"] = "2026-07-25 00:00+0300"
    catalog.save(str(po_path))


def main() -> None:
    """Update every project-owned Django catalog."""
    messages = collect_messages()
    for po_path in sorted((BASE_DIR / "locale").glob("*/LC_MESSAGES/django.po")):
        update_catalog(po_path, messages)
        untranslated = sum(1 for entry in polib.pofile(po_path) if not entry.msgstr)
        summary = (
            f"{po_path.relative_to(BASE_DIR)}: {len(messages)} messages, "
            f"{untranslated} untranslated"
        )
        print(summary)


if __name__ == "__main__":
    main()
