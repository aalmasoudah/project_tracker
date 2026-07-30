"""Pure Phase 13 date, spreadsheet-safety, and renderer tests."""

import re
from datetime import date
from io import BytesIO
from typing import Any, cast

import pytest
from django.db.models import QuerySet
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from apps.reports.datasets import ReportDocument, ReportTooLargeError, _bounded
from apps.reports.dates import format_dual_date
from apps.reports.renderers import (
    render_pdf,
    render_xlsx,
    safe_spreadsheet_value,
)


def sample_document(*, formula_value: str = "PRJ-13") -> ReportDocument:
    return ReportDocument(
        title="تقرير تقدم المشاريع",
        subtitle="جميع المشاريع المصرح بها",
        headers=("الرمز", "المشروع", "التاريخ"),
        rows=((formula_value, "مشروع التحول", "2026-07-30 م / 1448-02-15 هـ"),),
        filename_stem="project-progress",
        sheet_name="تقدم المشاريع",
    )


@pytest.mark.unit
def test_dual_date_uses_western_digits_and_hijri_markers() -> None:
    arabic = format_dual_date(date(2026, 7, 30), "ar")
    english = format_dual_date(date(2026, 7, 30), "en")

    assert arabic.startswith("2026-07-30 م / ")
    assert arabic.endswith(" هـ")
    assert english.startswith("2026-07-30 G / ")
    assert english.endswith(" AH")
    assert re.fullmatch(r"[0-9\- م/هـ]+", arabic)
    assert not re.search(r"[\u0660-\u0669]", arabic)


@pytest.mark.unit
@pytest.mark.parametrize("prefix", ("=", "+", "-", "@"))
def test_spreadsheet_formula_prefixes_are_neutralized(prefix: str) -> None:
    assert safe_spreadsheet_value(f"{prefix}SUM(A1:A2)").startswith("'")
    assert safe_spreadsheet_value("ordinary text") == "ordinary text"


@pytest.mark.unit
def test_arabic_excel_is_rtl_branded_and_formula_safe() -> None:
    payload = render_xlsx(sample_document(formula_value="=2+2"), language_code="ar")
    workbook = load_workbook(BytesIO(payload))
    sheet = cast(Worksheet, workbook.active)

    assert sheet.sheet_view.rightToLeft
    assert sheet["A6"].value == "'=2+2"
    assert sheet["A5"].fill.fgColor.rgb == "000A400C"
    assert len(cast(Any, sheet)._images) == 1


@pytest.mark.unit
def test_arabic_pdf_embeds_report_content_without_temporary_files() -> None:
    payload = render_pdf(sample_document(), language_code="ar")

    assert payload.startswith(b"%PDF-")
    assert len(payload) > 10_000


@pytest.mark.unit
def test_report_dataset_rejects_more_than_five_thousand_rows() -> None:
    oversized = cast(QuerySet[Any], list(range(5_001)))
    with pytest.raises(ReportTooLargeError):
        _bounded(oversized)
