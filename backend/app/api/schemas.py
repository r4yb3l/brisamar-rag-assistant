from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

BusinessLine = Literal["autos", "hogar", "vida"]
DocumentStatus = Literal["queued", "processing", "ready", "failed"]


class DocumentOut(BaseModel):
    id: UUID
    doc_key: str
    title: str
    business_line: BusinessLine
    version: int
    is_current: bool
    status: DocumentStatus
    error: str | None
    page_count: int | None
    chunk_count: int | None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentOut]


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    business_line: BusinessLine | None = None


class CitationOut(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    version: int
    page: int
    quote: str


class AskOut(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[CitationOut]
    trace_id: str | None


class ChunkOut(BaseModel):
    id: UUID
    document_id: UUID
    title: str
    doc_key: str
    version: int
    is_current: bool
    page: int
    text: str


class HealthOut(BaseModel):
    status: Literal["ok"]
