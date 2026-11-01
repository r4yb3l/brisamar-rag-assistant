import math

from app.llm.embeddings import FakeEmbeddingModel
from app.retrieval.hybrid import reciprocal_rank_fusion


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_fake_embeddings_are_deterministic_normalized_and_sized() -> None:
    [first] = FakeEmbeddingModel(dim=768).embed(["Plazo de declaración del siniestro"])
    [second] = FakeEmbeddingModel(dim=768).embed(["Plazo de declaración del siniestro"])
    assert first == second
    assert len(first) == 768
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)


def test_fake_embeddings_reflect_lexical_overlap() -> None:
    question, related, unrelated = FakeEmbeddingModel(dim=768).embed(
        [
            "¿Cuál es el plazo para declarar un siniestro?",
            "El asegurado debe declarar el siniestro en un plazo de cinco días.",
            "La capital de Francia es París.",
        ]
    )
    assert _cosine(question, related) > 0.3
    assert abs(_cosine(question, unrelated)) < 0.1


def test_rrf_rewards_items_ranked_by_both_retrievers() -> None:
    scores = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a"]], k=60)
    assert max(scores, key=scores.__getitem__) == "a"
    assert scores["c"] > scores["b"]
