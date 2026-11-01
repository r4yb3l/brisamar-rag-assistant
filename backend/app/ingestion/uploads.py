import hashlib
import re
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.ingestion.pdf import has_pdf_signature

DOC_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
_READ_BLOCK = 1024 * 1024


def slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")[:100]


def read_validated_pdf(upload: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in blocks, enforcing the size cap before buffering more than allowed."""
    buffer = bytearray()
    while block := upload.file.read(_READ_BLOCK):
        buffer.extend(block)
        if len(buffer) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB limit",
            )
    if not buffer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if not has_pdf_signature(bytes(buffer[:1024])):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted (missing %PDF- signature)",
        )
    return bytes(buffer)


def store_file(content: bytes, upload_dir: str) -> tuple[str, Path]:
    """Content-addressed storage: identical files share one path, so writes are idempotent."""
    digest = hashlib.sha256(content).hexdigest()
    directory = Path(upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.pdf"
    if not path.exists():
        temporary = directory / f"{digest}.{id(content)}.tmp"
        temporary.write_bytes(content)
        temporary.replace(path)
    return digest, path.resolve()
