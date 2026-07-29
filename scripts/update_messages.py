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


def python_messages(path: Path) -> tuple[set[str], dict[str, str]]:
    """Extract literal gettext calls from one Python module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    messages: set[str] = set()
    plural_messages: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function = node.func
        function_name = function.id if isinstance(function, ast.Name) else ""
        if function_name == "ngettext" and len(node.args) >= 2:
            singular = node.args[0]
            plural = node.args[1]
            if (
                isinstance(singular, ast.Constant)
                and isinstance(singular.value, str)
                and isinstance(plural, ast.Constant)
                and isinstance(plural.value, str)
            ):
                plural_messages[singular.value] = plural.value
            continue
        if function_name not in {"_", "gettext", "gettext_lazy"}:
            continue
        message = node.args[0]
        if isinstance(message, ast.Constant) and isinstance(message.value, str):
            messages.add(message.value)
    return messages, plural_messages


def template_messages(path: Path) -> set[str]:
    """Extract literal translate tags from one Django template."""
    source = path.read_text(encoding="utf-8")
    return {match.group("message") for match in TEMPLATE_TRANSLATE_RE.finditer(source)}


def collect_messages() -> tuple[set[str], dict[str, str]]:
    """Collect project-owned messages from Python and templates."""
    messages: set[str] = set()
    plural_messages: dict[str, str] = {}
    for source_root in SOURCE_ROOTS:
        for path in (BASE_DIR / source_root).rglob("*.py"):
            if "migrations" not in path.parts:
                source_messages, source_plurals = python_messages(path)
                messages.update(source_messages)
                plural_messages.update(source_plurals)
    for path in (BASE_DIR / "templates").rglob("*.html"):
        messages.update(template_messages(path))
    return messages, plural_messages


def update_catalog(
    po_path: Path,
    messages: set[str],
    plural_messages: dict[str, str],
) -> None:
    """Merge extracted messages into a catalog without discarding translations."""
    catalog = polib.pofile(po_path)
    existing = {entry.msgid: entry for entry in catalog if not entry.obsolete}
    for message in sorted(messages):
        if message not in existing and message not in plural_messages:
            catalog.append(polib.POEntry(msgid=message, msgstr=""))
    plural_forms = catalog.metadata.get("Plural-Forms", "")
    match = re.search(r"nplurals=(\d+)", plural_forms)
    plural_count = int(match.group(1)) if match else 2
    for singular, plural in sorted(plural_messages.items()):
        entry = existing.get(singular)
        if entry is None:
            catalog.append(
                polib.POEntry(
                    msgid=singular,
                    msgid_plural=plural,
                    msgstr_plural=dict.fromkeys(range(plural_count), ""),
                )
            )
        elif entry.msgid_plural != plural:
            entry.msgid_plural = plural
            entry.msgstr_plural = dict.fromkeys(range(plural_count), "")
            entry.msgstr = ""
    active_messages = messages | set(plural_messages)
    for entry in catalog:
        if entry.msgid and entry.msgid not in active_messages:
            entry.obsolete = True
    catalog.metadata["POT-Creation-Date"] = "2026-07-25 00:00+0300"
    catalog.save(str(po_path))


def main() -> None:
    """Update every project-owned Django catalog."""
    messages, plural_messages = collect_messages()
    for po_path in sorted((BASE_DIR / "locale").glob("*/LC_MESSAGES/django.po")):
        update_catalog(po_path, messages, plural_messages)
        catalog = polib.pofile(po_path)
        untranslated = sum(
            1 for entry in catalog if not entry.obsolete and not entry.translated()
        )
        summary = (
            f"{po_path.relative_to(BASE_DIR)}: "
            f"{len(messages) + len(plural_messages)} messages, "
            f"{untranslated} untranslated"
        )
        print(summary)


if __name__ == "__main__":
    main()
