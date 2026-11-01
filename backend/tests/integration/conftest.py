import os
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest

if not os.environ.get("DATABASE_URL") or not os.environ.get("DATABASE_ADMIN_URL"):
    pytest.skip(
        "integration tests need DATABASE_URL and DATABASE_ADMIN_URL (pgvector Postgres)",
        allow_module_level=True,
    )

os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="brisamar-uploads-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.migrate import run_migrations  # noqa: E402
from app.main import app  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parents[3] / "samples"
pytestmark = pytest.mark.integration


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    run_migrations()


@pytest.fixture(autouse=True)
def clean_tables() -> None:
    with psycopg.connect(os.environ["DATABASE_ADMIN_URL"], autocommit=True) as conn:
        conn.execute("TRUNCATE chunks, documents, embedding_cache")


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def upload(client: TestClient) -> Callable[..., dict[str, Any]]:
    def _upload(
        filename: str, business_line: str, doc_key: str, token: str = "analyst-all"
    ) -> dict[str, Any]:
        response = client.post(
            "/api/documents",
            headers=auth(token),
            data={"business_line": business_line, "doc_key": doc_key},
            files={"file": (filename, (SAMPLES_DIR / filename).read_bytes(), "application/pdf")},
        )
        assert response.status_code == 202, response.text
        return wait_for_terminal_status(client, response.json()["id"], token)

    return _upload


def wait_for_terminal_status(
    client: TestClient, document_id: str, token: str, timeout_s: float = 30
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while True:
        document = client.get(f"/api/documents/{document_id}", headers=auth(token)).json()
        if document["status"] in ("ready", "failed") or time.monotonic() > deadline:
            return document
        time.sleep(0.2)
