"""Two-stage hybrid retrieval: pgvector cosine search and Postgres full-text search, fused with RRF.

Both stages filter on ``business_line`` and on the current, ready version of each document. The
same restriction is enforced again by Row Level Security, because the queries run inside
``scoped_transaction``.
"""

from collections.abc import Sequence
from typing import Any

from pgvector import Vector
from psycopg import Connection

from app.retrieval.types import RetrievedChunk

_VECTOR_SQL = """
SELECT c.id AS chunk_id, c.document_id, d.doc_key, d.title, d.version, c.page, c.text,
       1 - (c.embedding <=> %(embedding)s) AS similarity
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.business_line = ANY(%(lines)s) AND d.is_current AND d.status = 'ready'
ORDER BY c.embedding <=> %(embedding)s
LIMIT %(limit)s
"""

_LEXICAL_SQL = """
WITH query AS (
    SELECT to_tsquery('simple', coalesce(
        (SELECT string_agg(quote_literal(lexeme), ' | ')
         FROM unnest(tsvector_to_array(to_tsvector('spanish', %(question)s))) AS lexeme),
        '')) AS tsq
)
SELECT c.id AS chunk_id, c.document_id, d.doc_key, d.title, d.version, c.page, c.text,
       ts_rank_cd(c.tsv, query.tsq) AS rank
FROM chunks c
JOIN documents d ON d.id = c.document_id
CROSS JOIN query
WHERE c.tsv @@ query.tsq
  AND c.business_line = ANY(%(lines)s) AND d.is_current AND d.status = 'ready'
ORDER BY rank DESC
LIMIT %(limit)s
"""


def reciprocal_rank_fusion(rankings: Sequence[Sequence[Any]], k: int) -> dict[Any, float]:
    scores: dict[Any, float] = {}
    for ranking in rankings:
        for position, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + position)
    return scores


def hybrid_search(
    conn: Connection,
    question: str,
    embedding: list[float],
    business_lines: Sequence[str],
    candidates: int,
    top_k: int,
    rrf_k: int,
) -> list[RetrievedChunk]:
    lines = list(business_lines)
    vector_rows = conn.execute(
        _VECTOR_SQL,
        {"embedding": Vector(embedding), "lines": lines, "limit": candidates},
    ).fetchall()
    lexical_rows = conn.execute(
        _LEXICAL_SQL, {"question": question, "lines": lines, "limit": candidates}
    ).fetchall()

    rows_by_id = {row["chunk_id"]: row for row in [*lexical_rows, *vector_rows]}
    vector_ids = [row["chunk_id"] for row in vector_rows]
    lexical_ids = [row["chunk_id"] for row in lexical_rows]
    similarity = {row["chunk_id"]: float(row["similarity"]) for row in vector_rows}
    fused = reciprocal_rank_fusion([vector_ids, lexical_ids], rrf_k)

    ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]
    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=rows_by_id[chunk_id]["document_id"],
            doc_key=rows_by_id[chunk_id]["doc_key"],
            title=rows_by_id[chunk_id]["title"],
            version=rows_by_id[chunk_id]["version"],
            page=rows_by_id[chunk_id]["page"],
            text=rows_by_id[chunk_id]["text"],
            vector_similarity=similarity.get(chunk_id),
            vector_rank=vector_ids.index(chunk_id) + 1 if chunk_id in similarity else None,
            lexical_rank=lexical_ids.index(chunk_id) + 1 if chunk_id in lexical_ids else None,
            fused_score=score,
        )
        for chunk_id, score in ranked
    ]
