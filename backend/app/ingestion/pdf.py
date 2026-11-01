from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_MAGIC = b"%PDF-"
MIN_DOCUMENT_CHARS = 40


class PermanentIngestionError(Exception):
    """The file can never be ingested as-is; retrying will not help."""


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def has_pdf_signature(head: bytes) -> bool:
    return head.lstrip(b"\x00\t\r\n ")[: len(PDF_MAGIC)] == PDF_MAGIC


def extract_pages(path: Path, max_pages: int) -> list[PageText]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise PermanentIngestionError("The PDF is password-protected.")
        if len(reader.pages) > max_pages:
            raise PermanentIngestionError(
                f"The PDF has {len(reader.pages)} pages; the limit is {max_pages}."
            )
        pages = [
            PageText(page=number, text=(page.extract_text() or "").strip())
            for number, page in enumerate(reader.pages, start=1)
        ]
    except PermanentIngestionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as error:
        raise PermanentIngestionError(f"The PDF is corrupt or unreadable: {error}") from error
    if sum(len(page.text) for page in pages) < MIN_DOCUMENT_CHARS:
        raise PermanentIngestionError(
            "The PDF has no extractable text (probably a scanned image). OCR is not supported."
        )
    return [page for page in pages if page.text]
