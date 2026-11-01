import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.answering.service import answer_question
from app.api.schemas import (
    AskIn,
    AskOut,
    BusinessLine,
    ChunkOut,
    CitationOut,
    DocumentList,
    DocumentOut,
    HealthOut,
)
from app.core.auth import Principal, get_principal, resolve_business_lines
from app.core.config import Settings, get_settings
from app.db import documents as repo
from app.db.session import scoped_transaction
from app.ingestion.uploads import DOC_KEY_PATTERN, read_validated_pdf, slugify, store_file
from app.llm.chat import ChatModel, get_chat_model
from app.llm.embeddings import EmbeddingModel, get_embedding_model
from app.llm.errors import LLMUnavailableError
from app.observability.tracing import current_trace_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

PrincipalDep = Annotated[Principal, Depends(get_principal)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_embedder(settings: SettingsDep) -> EmbeddingModel:
    return get_embedding_model(settings)


def get_chat(settings: SettingsDep) -> ChatModel:
    return get_chat_model(settings)


def _document_out(row: dict[str, Any]) -> DocumentOut:
    return DocumentOut.model_validate(row)


def _enqueue_ingestion(document_id: UUID, business_line: str) -> None:
    from app.worker import ingest_document_task

    ingest_document_task.apply_async(args=[str(document_id), business_line])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok")


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    principal: PrincipalDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
    business_line: Annotated[BusinessLine, Form()],
    doc_key: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> DocumentOut:
    lines = resolve_business_lines(principal, business_line)
    stem = Path(file.filename or "document.pdf").stem
    key = slugify(doc_key or stem)
    if not DOC_KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="doc_key must contain letters or digits",
        )
    content = read_validated_pdf(file, settings.max_upload_bytes)
    sha256, path = store_file(content, settings.upload_dir)

    with scoped_transaction(lines) as conn:
        registered = repo.register_upload(
            conn,
            doc_key=key,
            title=(title or stem).strip() or key,
            business_line=business_line,
            file_sha256=sha256,
            file_path=str(path),
        )
    document = registered.row
    logger.info(
        "document registered",
        extra={
            "document_id": str(document["id"]),
            "doc_key": key,
            "version": document["version"],
            "needs_ingestion": registered.needs_ingestion,
        },
    )
    if not registered.needs_ingestion:
        return _document_out(document)
    try:
        _enqueue_ingestion(document["id"], business_line)
    except Exception as error:
        logger.exception("could not enqueue ingestion", extra={"document_id": str(document["id"])})
        with scoped_transaction(lines) as conn:
            repo.set_status(conn, document["id"], "failed", "Ingestion queue unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion queue unavailable; retry the upload",
        ) from error
    with scoped_transaction(lines) as conn:
        refreshed = repo.get_document(conn, document["id"])
    return _document_out(refreshed or document)


@router.get("/documents", response_model=DocumentList)
def list_documents(
    principal: PrincipalDep, business_line: Annotated[BusinessLine | None, Query()] = None
) -> DocumentList:
    lines = resolve_business_lines(principal, business_line)
    with scoped_transaction(lines) as conn:
        rows = repo.list_documents(conn, list(lines))
    return DocumentList(items=[_document_out(row) for row in rows])


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, principal: PrincipalDep) -> DocumentOut:
    with scoped_transaction(principal.business_lines) as conn:
        row = repo.get_document(conn, document_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _document_out(row)


@router.get("/chunks/{chunk_id}", response_model=ChunkOut)
def get_chunk(chunk_id: UUID, principal: PrincipalDep) -> ChunkOut:
    with scoped_transaction(principal.business_lines) as conn:
        row = repo.get_chunk(conn, chunk_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return ChunkOut.model_validate(row)


@router.post("/ask", response_model=AskOut)
def ask(
    body: AskIn,
    principal: PrincipalDep,
    settings: SettingsDep,
    embedder: Annotated[EmbeddingModel, Depends(get_embedder)],
    chat_model: Annotated[ChatModel, Depends(get_chat)],
) -> AskOut:
    lines = resolve_business_lines(principal, body.business_line)
    try:
        result = answer_question(body.question, lines, embedder, chat_model, settings)
    except LLMUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language model provider is unavailable; try again shortly",
        ) from error
    return AskOut(
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason.value if result.refusal_reason else None,
        confidence=result.confidence,
        citations=[
            CitationOut(
                chunk_id=citation.chunk.chunk_id,
                document_id=citation.chunk.document_id,
                title=citation.chunk.title,
                version=citation.chunk.version,
                page=citation.chunk.page,
                quote=citation.quote,
            )
            for citation in result.citations
        ],
        trace_id=current_trace_id(),
    )
