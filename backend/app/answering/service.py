import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from app.answering.citations import validate_citations
from app.answering.generator import InvalidModelOutputError, generate_answer
from app.core.config import Settings
from app.db.session import scoped_transaction
from app.llm.chat import ChatModel
from app.llm.embeddings import EmbeddingModel, embed_traced
from app.llm.prompt import build_sources
from app.observability.tracing import tracer
from app.retrieval.hybrid import hybrid_search
from app.retrieval.types import RetrievedChunk

logger = logging.getLogger(__name__)

REFUSAL_ANSWER = (
    "No encuentro evidencia suficiente en los documentos disponibles para responder con "
    "seguridad. Revisa el manual vigente o consulta con el responsable de procedimientos."
)


class RefusalReason(StrEnum):
    NO_RELEVANT_EVIDENCE = "no_relevant_evidence"
    MODEL_INSUFFICIENT_EVIDENCE = "model_insufficient_evidence"
    UNGROUNDED_ANSWER = "ungrounded_answer"
    INVALID_MODEL_OUTPUT = "invalid_model_output"


@dataclass(frozen=True)
class GroundedCitation:
    chunk: RetrievedChunk
    quote: str


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    refusal_reason: RefusalReason | None
    confidence: float
    citations: list[GroundedCitation] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        return self.refusal_reason is not None


def _refuse(reason: RefusalReason) -> AnswerResult:
    return AnswerResult(answer=REFUSAL_ANSWER, refusal_reason=reason, confidence=0.0)


def min_similarity(settings: Settings, embedder: EmbeddingModel) -> float:
    if settings.min_vector_similarity is not None:
        return settings.min_vector_similarity
    return embedder.default_min_similarity


def retrieve(
    question: str,
    business_lines: Sequence[str],
    embedder: EmbeddingModel,
    settings: Settings,
) -> list[RetrievedChunk]:
    [query_embedding] = embed_traced(embedder, [question], purpose="query")
    with (
        tracer.start_as_current_span("retrieval.hybrid") as span,
        scoped_transaction(business_lines) as conn,
    ):
        chunks = hybrid_search(
            conn,
            question,
            query_embedding,
            business_lines,
            candidates=settings.retrieval_candidates,
            top_k=settings.retrieval_top_k,
            rrf_k=settings.rrf_k,
        )
        span.set_attribute("retrieval.business_lines", list(business_lines))
        span.set_attribute("retrieval.returned", len(chunks))
        span.set_attribute("retrieval.top_similarity", top_similarity(chunks))
        return chunks


def top_similarity(chunks: Sequence[RetrievedChunk]) -> float:
    return max((c.vector_similarity or 0.0 for c in chunks), default=0.0)


def answer_question(
    question: str,
    business_lines: Sequence[str],
    embedder: EmbeddingModel,
    chat_model: ChatModel,
    settings: Settings,
) -> AnswerResult:
    chunks = retrieve(question, business_lines, embedder, settings)
    evidence = top_similarity(chunks)
    threshold = min_similarity(settings, embedder)
    if not chunks or evidence < threshold:
        logger.info(
            "refusing: evidence below threshold",
            extra={"top_similarity": round(evidence, 4), "threshold": threshold},
        )
        return _refuse(RefusalReason.NO_RELEVANT_EVIDENCE)

    sources = build_sources(chunks)
    if any(source.flagged for source in sources):
        logger.warning(
            "retrieved chunks contain instruction-like text",
            extra={"chunk_ids": [str(s.chunk.chunk_id) for s in sources if s.flagged]},
        )
    try:
        model_answer = generate_answer(chat_model, question, sources)
    except InvalidModelOutputError:
        return _refuse(RefusalReason.INVALID_MODEL_OUTPUT)
    if model_answer.insufficient_evidence or not model_answer.answer.strip():
        return _refuse(RefusalReason.MODEL_INSUFFICIENT_EVIDENCE)

    report = validate_citations(model_answer.citations, sources)
    if report.dropped_unknown or report.repaired_quotes:
        logger.warning(
            "citations repaired",
            extra={"dropped": report.dropped_unknown, "repaired": report.repaired_quotes},
        )
    if not report.citations:
        return _refuse(RefusalReason.UNGROUNDED_ANSWER)

    return AnswerResult(
        answer=model_answer.answer.strip(),
        refusal_reason=None,
        confidence=round(min(model_answer.confidence, evidence), 2),
        citations=[GroundedCitation(c.source.chunk, c.quote) for c in report.citations],
    )
