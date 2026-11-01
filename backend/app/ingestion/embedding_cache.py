import hashlib

from pgvector import Vector
from psycopg import Connection

from app.llm.embeddings import EmbeddingModel, embed_traced
from app.observability.tracing import tracer


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_with_cache(
    conn: Connection, model: EmbeddingModel, texts: list[str]
) -> list[list[float]]:
    """Embed ``texts``, reusing vectors keyed by (sha256(text), model) from earlier ingestions."""
    hashes = [content_hash(text) for text in texts]
    with tracer.start_as_current_span("embedding.cache_lookup") as span:
        rows = conn.execute(
            "SELECT content_hash, embedding FROM embedding_cache "
            "WHERE model = %s AND content_hash = ANY(%s)",
            (model.name, list(set(hashes))),
        ).fetchall()
        cached = {row["content_hash"]: row["embedding"].to_list() for row in rows}
        missing = list(dict.fromkeys(h for h in hashes if h not in cached))
        span.set_attribute("embedding.cache_hits", len(hashes) - sum(h in missing for h in hashes))
        span.set_attribute("embedding.cache_misses", len(missing))
    if missing:
        text_by_hash = dict(zip(hashes, texts, strict=True))
        vectors = embed_traced(model, [text_by_hash[h] for h in missing], purpose="ingestion")
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO embedding_cache (content_hash, model, embedding) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                [(h, model.name, Vector(v)) for h, v in zip(missing, vectors, strict=True)],
            )
        cached.update(zip(missing, vectors, strict=True))
    return [cached[h] for h in hashes]
