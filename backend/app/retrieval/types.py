from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    doc_key: str
    title: str
    version: int
    page: int
    text: str
    vector_similarity: float | None
    lexical_rank: int | None
    vector_rank: int | None
    fused_score: float
