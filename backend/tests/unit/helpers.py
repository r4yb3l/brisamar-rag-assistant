import uuid

from app.llm.prompt import PromptSource, build_sources
from app.retrieval.types import RetrievedChunk


def make_chunk(text: str, page: int = 1, similarity: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        doc_key="manual",
        title="Manual",
        version=1,
        page=page,
        text=text,
        vector_similarity=similarity,
        lexical_rank=1,
        vector_rank=1,
        fused_score=0.03,
    )


def make_sources(*texts: str) -> list[PromptSource]:
    return build_sources([make_chunk(text) for text in texts])
