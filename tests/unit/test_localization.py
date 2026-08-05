"""Arabic identity normalization and terminology tests."""

from pathlib import Path

import pytest
from django.utils import translation

from apps.accounts.normalization import normalize_account_search
from apps.accounts.roles import PROJECT_MANAGER, role_label
from scripts.update_messages import template_messages


@pytest.mark.unit
def test_arabic_search_normalization_is_conservative() -> None:
    assert normalize_account_search("  إِبـرَاهِيم کاظم  ") == "ابراهيم كاظم"
    assert normalize_account_search("مدرسة") != normalize_account_search("مدرسه")
    assert normalize_account_search("هدى") != normalize_account_search("هدي")


@pytest.mark.unit
def test_approved_role_label_is_localized() -> None:
    with translation.override("ar"):
        assert str(role_label(PROJECT_MANAGER)) == "مدير مشروع"

    with translation.override("en"):
        assert str(role_label(PROJECT_MANAGER)) == "Project Manager"


@pytest.mark.unit
def test_windows_catalog_updater_preserves_blocktranslate_messages(
    tmp_path: Path,
) -> None:
    template = tmp_path / "sample.html"
    template.write_text(
        "{% blocktranslate with reviewer=user.display_name %}"
        "Reviewed by {{ reviewer }}."
        "{% endblocktranslate %}",
        encoding="utf-8",
    )

    assert "Reviewed by %(reviewer)s." in template_messages(template)
