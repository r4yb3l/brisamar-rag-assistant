from app.ingestion.chunking import chunk_page, chunk_pages, normalize_page_text
from app.ingestion.pdf import PageText


def test_normalize_joins_hyphenated_line_breaks_and_collapses_whitespace() -> None:
    assert normalize_page_text("decla-\nración   del\n siniestro") == "declaración del siniestro"


def test_short_page_is_a_single_chunk() -> None:
    assert chunk_page("Una frase. Otra frase.", max_chars=200, overlap_chars=50) == [
        "Una frase. Otra frase."
    ]


def test_chunks_respect_max_size_and_overlap_previous_sentence() -> None:
    sentences = [f"Regla número {i} del procedimiento de siniestros." for i in range(20)]
    chunks = chunk_page(" ".join(sentences), max_chars=200, overlap_chars=60)
    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        last_sentence = previous.rsplit(". ", 1)[-1]
        assert current.startswith(last_sentence)


def test_overly_long_sentence_is_split_by_words() -> None:
    chunks = chunk_page("palabra " * 300, max_chars=100, overlap_chars=0)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert sum(chunk.count("palabra") for chunk in chunks) == 300


def test_chunks_never_cross_pages_and_ordinals_are_global() -> None:
    pages = [PageText(1, "Texto de la página uno."), PageText(3, "Texto de la página tres.")]
    chunks = chunk_pages(pages, max_chars=500, overlap_chars=100)
    assert [(c.ordinal, c.page) for c in chunks] == [(0, 1), (1, 3)]
    assert "tres" not in chunks[0].text
