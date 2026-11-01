import logging
import uuid
from pathlib import Path
from uuid import UUID

from pgvector import Vector

from app.core.config import Settings
from app.db import documents as repo
from app.db.session import scoped_transaction
from app.ingestion.chunking import chunk_pages
from app.ingestion.embedding_cache import content_hash, embed_with_cache
from app.ingestion.pdf import PermanentIngestionError, extract_pages
from app.llm.embeddings import EmbeddingModel
from app.observability.tracing import tracer

logger = logging.getLogger(__name__)

CHUNK_NAMESPACE = uuid.UUID("0b5c3a64-5f0e-4c39-9a52-6f7c2d1e8a90")


def chunk_id(document_id: UUID, ordinal: int) -> UUID:
    """Deterministic id: a retried task rewrites the same chunk ids, so citations stay stable."""
    return uuid.uuid5(CHUNK_NAMESPACE, f"{document_id}:{ordinal}")


def ingest_document(
    document_id: UUID, business_line: str, embedder: EmbeddingModel, settings: Settings
) -> str:
    """Run extraction → chunking → embedding → storage for one document version.

    Returns the final status. Safe to run more than once: chunks are replaced in a single
    transaction together with the status change, so a crash halfway leaves either the previous
    state or the complete new one.
    """
    lines = [business_line]
    with scoped_transaction(lines) as conn:
        document = repo.get_document(conn, document_id)
        if document is None:
            raise LookupError(f"Document {document_id} not found")
        if document["status"] == "ready":
            logger.info("document already ingested", extra={"document_id": str(document_id)})
            return "ready"
        repo.set_status(conn, document_id, "processing")

    try:
        with tracer.start_as_current_span("ingestion.extract") as span:
            pages = extract_pages(Path(document["file_path"]), settings.max_pdf_pages)
            span.set_attribute("ingestion.page_count", len(pages))
        with tracer.start_as_current_span("ingestion.chunk") as span:
            chunks = chunk_pages(pages, settings.chunk_max_chars, settings.chunk_overlap_chars)
            span.set_attribute("ingestion.chunk_count", len(chunks))
    except PermanentIngestionError as error:
        logger.warning(
            "document rejected", extra={"document_id": str(document_id), "reason": str(error)}
        )
        with scoped_transaction(lines) as conn:
            repo.set_status(conn, document_id, "failed", str(error))
        return "failed"

    with scoped_transaction(lines) as conn:
        vectors = embed_with_cache(conn, embedder, [chunk.text for chunk in chunks])

    with tracer.start_as_current_span("ingestion.store") as span, scoped_transaction(lines) as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO chunks (id, document_id, business_line, ordinal, page, text, "
                "content_hash, embedding) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        chunk_id(document_id, chunk.ordinal),
                        document_id,
                        business_line,
                        chunk.ordinal,
                        chunk.page,
                        chunk.text,
                        content_hash(chunk.text),
                        Vector(vector),
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )
        conn.execute(
            "UPDATE documents SET status = 'ready', error = NULL, page_count = %s, "
            "chunk_count = %s, updated_at = now() WHERE id = %s",
            (max(page.page for page in pages), len(chunks), document_id),
        )
        repo.promote_latest_ready_version(conn, business_line, document["doc_key"])
        span.set_attribute("ingestion.chunks_written", len(chunks))
    logger.info(
        "document ingested",
        extra={"document_id": str(document_id), "chunks": len(chunks), "pages": len(pages)},
    )
    return "ready"


def mark_failed(document_id: UUID, business_line: str, message: str) -> None:
    with scoped_transaction([business_line]) as conn:
        repo.set_status(conn, document_id, "failed", message)
