import io

import pytest
from fastapi import HTTPException, UploadFile

from app.core.auth import DEMO_TOKENS, resolve_business_lines
from app.ingestion.pdf import has_pdf_signature
from app.ingestion.uploads import read_validated_pdf, slugify


def _upload(content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename="x.pdf")


def test_pdf_signature_is_checked_on_content_not_extension() -> None:
    assert has_pdf_signature(b"%PDF-1.7\n...")
    assert not has_pdf_signature(b"PK\x03\x04 zip disguised as pdf")


def test_rejects_oversized_and_non_pdf_uploads() -> None:
    with pytest.raises(HTTPException) as too_big:
        read_validated_pdf(_upload(b"%PDF-" + b"0" * 2048), max_bytes=1024)
    assert too_big.value.status_code == 413
    with pytest.raises(HTTPException) as not_pdf:
        read_validated_pdf(_upload(b"<html>hola</html>"), max_bytes=1024)
    assert not_pdf.value.status_code == 415


def test_slugify_produces_safe_doc_keys() -> None:
    assert slugify("Manual Siniestros Autos (v2)") == "manual-siniestros-autos-v2"
    assert slugify("Circular Prestación Vida") == "circular-prestacion-vida"


def test_business_line_scope_is_enforced() -> None:
    autos = DEMO_TOKENS["analyst-autos"]
    assert resolve_business_lines(autos, None) == ("autos",)
    with pytest.raises(HTTPException) as forbidden:
        resolve_business_lines(autos, "vida")
    assert forbidden.value.status_code == 403
