"""Upload the sample manuals through the public API and wait until they are processed.

Standard library only, so it runs with any Python 3.10+:
    python scripts/seed.py [--api http://localhost:8000] [--with-failures]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"
TOKEN = "analyst-all"

UPLOADS = [
    (
        "manual-siniestros-autos-v1.pdf",
        "autos",
        "manual-siniestros-autos",
        "Manual de siniestros de Autos",
    ),
    (
        "manual-siniestros-autos-v2.pdf",
        "autos",
        "manual-siniestros-autos",
        "Manual de siniestros de Autos",
    ),
    (
        "circular-antifraude-autos.pdf",
        "autos",
        "circular-antifraude-autos",
        "Circular antifraude de Autos",
    ),
    (
        "manual-siniestros-hogar.pdf",
        "hogar",
        "manual-siniestros-hogar",
        "Manual de siniestros de Hogar",
    ),
    (
        "circular-prestaciones-vida.pdf",
        "vida",
        "circular-prestaciones-vida",
        "Circular de prestaciones de Vida",
    ),
]
FAILURE_UPLOADS = [
    ("corrupto.pdf", "hogar", "pdf-corrupto", "PDF corrupto (prueba)"),
    ("escaneado-sin-texto.pdf", "vida", "pdf-escaneado", "PDF escaneado sin texto (prueba)"),
]


def _multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{file_path.name}"\r\nContent-Type: application/pdf\r\n\r\n'
        ).encode()
        + file_path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _request(
    api: str, method: str, path: str, body: bytes | None = None, content_type: str | None = None
) -> dict:
    request = urllib.request.Request(f"{api}{path}", data=body, method=method)
    request.add_header("Authorization", f"Bearer {TOKEN}")
    if content_type:
        request.add_header("Content-Type", content_type)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def _wait_until_processed(api: str, document_id: str, timeout_s: float = 120) -> dict:
    deadline = time.monotonic() + timeout_s
    while True:
        document = _request(api, "GET", f"/api/documents/{document_id}")
        if document["status"] in ("ready", "failed") or time.monotonic() > deadline:
            return document
        time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--with-failures", action="store_true", help="also upload broken PDFs")
    args = parser.parse_args()

    uploads = UPLOADS + (FAILURE_UPLOADS if args.with_failures else [])
    for filename, business_line, doc_key, title in uploads:
        body, content_type = _multipart(
            {"business_line": business_line, "doc_key": doc_key, "title": title},
            SAMPLES_DIR / filename,
        )
        try:
            created = _request(args.api, "POST", "/api/documents", body, content_type)
        except urllib.error.HTTPError as error:
            print(f"{filename}: HTTP {error.code} {error.read().decode()}", file=sys.stderr)
            return 1
        document = _wait_until_processed(args.api, created["id"])
        print(
            f"{filename:34} -> {document['doc_key']} v{document['version']} "
            f"[{document['status']}] chunks={document['chunk_count']} "
            f"current={document['is_current']} {document['error'] or ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
