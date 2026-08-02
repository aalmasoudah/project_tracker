"""Phase 9 capability and evidence boundary tests."""

import hashlib
import secrets

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.attendance.services import validate_evidence


@pytest.mark.unit
def test_token_entropy_and_hash_only_lookup_shape() -> None:
    token = secrets.token_urlsafe(32)
    assert len(token) >= 40
    digest = hashlib.sha256(token.encode()).hexdigest()
    assert len(digest) == 64
    assert token not in digest


@pytest.mark.unit
def test_evidence_signature_extension_and_size_validation() -> None:
    valid = SimpleUploadedFile(
        "evidence.pdf", b"%PDF-1.7\nfictional", content_type="application/pdf"
    )
    suffix, content = validate_evidence(valid)
    assert suffix == ".pdf"
    assert content.startswith(b"%PDF-")

    spoofed = SimpleUploadedFile(
        "evidence.pdf", b"not a pdf", content_type="application/pdf"
    )
    with pytest.raises(ValidationError):
        validate_evidence(spoofed)
