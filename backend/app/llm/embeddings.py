import hashlib
import math
import time
from typing import Protocol

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.llm.errors import LLMUnavailableError, is_transient_llm_error
from app.llm.text import content_terms
from app.observability.tracing import tracer


class EmbeddingModel(Protocol):
    name: str
    dim: int
    default_min_similarity: float

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class FakeEmbeddingModel:
    """Deterministic, offline embeddings: a signed hashed bag of content terms."""

    name = "fake/hashed-bow-v1"
    default_min_similarity = 0.15

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for term in content_terms(text):
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        return _normalize(vector)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]


class LiteLLMEmbeddingModel:
    default_min_similarity = 0.6
    batch_size = 64

    def __init__(self, settings: Settings) -> None:
        self.name = settings.embedding_model
        self.dim = settings.embedding_dim
        self._timeout = settings.llm_timeout_seconds
        self._max_attempts = settings.llm_max_attempts

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed_batch(texts[start : start + self.batch_size]))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        import litellm

        @retry(
            retry=retry_if_exception(is_transient_llm_error),
            wait=wait_exponential(multiplier=0.5, max=8),
            stop=stop_after_attempt(self._max_attempts),
            reraise=True,
        )
        def call() -> list[list[float]]:
            response = litellm.embedding(
                model=self.name,
                input=texts,
                dimensions=self.dim,
                timeout=self._timeout,
            )
            return [_normalize(list(item["embedding"])) for item in response.data]

        try:
            return call()
        except Exception as error:
            if is_transient_llm_error(error):
                raise LLMUnavailableError(f"Embedding provider unavailable: {error}") from error
            raise


def get_embedding_model(settings: Settings | None = None) -> EmbeddingModel:
    settings = settings or get_settings()
    if settings.embedding_provider == "litellm":
        return LiteLLMEmbeddingModel(settings)
    return FakeEmbeddingModel(settings.embedding_dim)


def embed_traced(model: EmbeddingModel, texts: list[str], purpose: str) -> list[list[float]]:
    with tracer.start_as_current_span("embedding.embed") as span:
        span.set_attribute("embedding.model", model.name)
        span.set_attribute("embedding.purpose", purpose)
        span.set_attribute("embedding.input_count", len(texts))
        started = time.perf_counter()
        vectors = model.embed(texts)
        span.set_attribute("embedding.latency_ms", round((time.perf_counter() - started) * 1000, 1))
        return vectors
