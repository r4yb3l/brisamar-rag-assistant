from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg import Connection

DOCUMENT_COLUMNS = (
    "id, doc_key, title, business_line, version, is_current, status, error, "
    "page_count, chunk_count, created_at, file_path, file_sha256"
)


@dataclass(frozen=True)
class RegisteredDocument:
    row: dict[str, Any]
    needs_ingestion: bool


def _lock_doc_key(conn: Connection, business_line: str, doc_key: str) -> None:
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"{business_line}/{doc_key}",)
    )


def register_upload(
    conn: Connection,
    *,
    doc_key: str,
    title: str,
    business_line: str,
    file_sha256: str,
    file_path: str,
) -> RegisteredDocument:
    """Create version N+1 of ``doc_key``, or reuse the version that already holds this exact file.

    A byte-identical re-upload returns the existing version instead of re-embedding it. If that
    version previously failed it is re-queued, which turns a re-upload into a retry.
    """
    _lock_doc_key(conn, business_line, doc_key)
    existing = conn.execute(
        f"SELECT {DOCUMENT_COLUMNS} FROM documents "
        "WHERE business_line = %s AND doc_key = %s AND file_sha256 = %s "
        "ORDER BY version DESC LIMIT 1",
        (business_line, doc_key, file_sha256),
    ).fetchone()
    if existing and existing["status"] != "failed":
        return RegisteredDocument(existing, needs_ingestion=False)
    if existing:
        requeued = conn.execute(
            f"UPDATE documents SET status = 'queued', error = NULL, updated_at = now() "
            f"WHERE id = %s RETURNING {DOCUMENT_COLUMNS}",
            (existing["id"],),
        ).fetchone()
        return RegisteredDocument(requeued, needs_ingestion=True)
    created = conn.execute(
        f"""
        INSERT INTO documents (doc_key, title, business_line, version, file_sha256, file_path)
        SELECT %(doc_key)s, %(title)s, %(line)s, coalesce(max(version), 0) + 1, %(sha)s, %(path)s
        FROM documents WHERE business_line = %(line)s AND doc_key = %(doc_key)s
        RETURNING {DOCUMENT_COLUMNS}
        """,
        {
            "doc_key": doc_key,
            "title": title,
            "line": business_line,
            "sha": file_sha256,
            "path": file_path,
        },
    ).fetchone()
    return RegisteredDocument(created, needs_ingestion=True)


def get_document(conn: Connection, document_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"SELECT {DOCUMENT_COLUMNS} FROM documents WHERE id = %s", (document_id,)
    ).fetchone()


def list_documents(conn: Connection, business_lines: list[str]) -> list[dict[str, Any]]:
    return conn.execute(
        f"SELECT {DOCUMENT_COLUMNS} FROM documents WHERE business_line = ANY(%s) "
        "ORDER BY created_at DESC, version DESC",
        (business_lines,),
    ).fetchall()


def get_chunk(conn: Connection, chunk_id: UUID) -> dict[str, Any] | None:
    return conn.execute(
        """
        SELECT c.id, c.document_id, d.title, d.doc_key, d.version, d.is_current, c.page, c.text
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE c.id = %s
        """,
        (chunk_id,),
    ).fetchone()


def set_status(conn: Connection, document_id: UUID, status: str, error: str | None = None) -> None:
    conn.execute(
        "UPDATE documents SET status = %s, error = %s, updated_at = now() WHERE id = %s",
        (status, error, document_id),
    )


def promote_latest_ready_version(conn: Connection, business_line: str, doc_key: str) -> None:
    """Make the highest *ready* version current; out-of-order completions cannot demote it."""
    _lock_doc_key(conn, business_line, doc_key)
    conn.execute(
        """
        UPDATE documents SET is_current = false
        WHERE business_line = %(line)s AND doc_key = %(key)s AND is_current
        """,
        {"line": business_line, "key": doc_key},
    )
    conn.execute(
        """
        UPDATE documents SET is_current = true
        WHERE id = (
            SELECT id FROM documents
            WHERE business_line = %(line)s AND doc_key = %(key)s AND status = 'ready'
            ORDER BY version DESC LIMIT 1
        )
        """,
        {"line": business_line, "key": doc_key},
    )
