"""Phase 8 normalization and bounded parser tests."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.trainees.normalization import (
    normalize_trainee_phone,
    trainee_identity_key,
)
from apps.trainees.services import _read_xlsx, validate_import_file


@pytest.mark.unit
def test_phone_and_arabic_identity_normalization_is_non_destructive() -> None:
    assert normalize_trainee_phone("05 0000 0001") == "966500000001"
    assert normalize_trainee_phone("+966-50-000-0001") == "966500000001"
    assert trainee_identity_key("أحمد  علي", "0500000001") == trainee_identity_key(
        "احمد علي", "+966500000001"
    )


@pytest.mark.unit
def test_import_file_boundaries_reject_spoofed_and_oversized_files() -> None:
    spoofed = SimpleUploadedFile(
        "trainees.csv", b"full_name,phone\nName,0500000001\n", content_type="image/png"
    )
    with pytest.raises(ValidationError):
        validate_import_file(spoofed)

    oversized = SimpleUploadedFile(
        "trainees.csv",
        b"x" * (5 * 1024 * 1024 + 1),
        content_type="text/csv",
    )
    with pytest.raises(ValidationError):
        validate_import_file(oversized)


@pytest.mark.unit
def test_xlsx_rejects_formula_and_accepts_arabic_headers() -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["الاسم الكامل", "رقم الجوال", "البريد الإلكتروني"])
    sheet.append(["متدرب خيالي", "0500000001", "=1+1"])
    stream = BytesIO()
    workbook.save(stream)
    with pytest.raises(ValidationError):
        _read_xlsx(stream.getvalue())

    safe_workbook = Workbook()
    safe_sheet = safe_workbook.active
    assert safe_sheet is not None
    safe_sheet.append(["الاسم الكامل", "رقم الجوال"])
    safe_sheet.append(["متدرب خيالي", "0500000001"])
    safe_stream = BytesIO()
    safe_workbook.save(safe_stream)
    headers, rows = _read_xlsx(safe_stream.getvalue())
    assert headers == ["full_name", "phone"]
    assert rows == [["متدرب خيالي", "0500000001"]]
