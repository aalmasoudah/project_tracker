"""Compile gettext catalogs without requiring a system gettext installation."""

from pathlib import Path

import polib

BASE_DIR = Path(__file__).resolve().parents[1]


def compile_catalog(po_path: Path) -> Path:
    """Compile one portable-object catalog and return the output path."""
    mo_path = po_path.with_suffix(".mo")
    catalog = polib.pofile(po_path)
    catalog.save_as_mofile(str(mo_path))
    return mo_path


def main() -> None:
    """Compile every project Django translation catalog."""
    po_files = sorted((BASE_DIR / "locale").glob("*/LC_MESSAGES/django.po"))
    if not po_files:
        raise SystemExit("No Django translation catalogs were found.")

    for po_path in po_files:
        output_path = compile_catalog(po_path)
        print(output_path.relative_to(BASE_DIR))


if __name__ == "__main__":
    main()
