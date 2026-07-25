"""Arabic identity normalization and terminology tests."""

import pytest
from django.utils import translation

from apps.accounts.normalization import normalize_account_search
from apps.accounts.roles import PROJECT_MANAGER, role_label


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
