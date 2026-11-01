from app.answering.citations import validate_citations
from app.llm.schemas import ModelCitation
from tests.unit.helpers import make_sources

SOURCES = make_sources(
    "El asegurado debe comunicar el siniestro en un plazo máximo de 5 días hábiles.",
    "La franquicia de lunas es de 60 euros por siniestro.",
)


def test_verbatim_quote_is_kept_despite_accent_and_case_differences() -> None:
    report = validate_citations(
        [ModelCitation(source_id="S1", quote="plazo maximo de 5 DIAS habiles")], SOURCES
    )
    assert len(report.citations) == 1
    assert report.citations[0].quote_verified
    assert report.citations[0].source.source_id == "S1"


def test_citation_to_unretrieved_source_is_dropped() -> None:
    report = validate_citations([ModelCitation(source_id="S9", quote="algo")], SOURCES)
    assert report.citations == []
    assert report.dropped_unknown == 1


def test_fabricated_quote_is_replaced_with_real_excerpt() -> None:
    report = validate_citations(
        [ModelCitation(source_id="S2", quote="La franquicia es de 500 euros")], SOURCES
    )
    [citation] = report.citations
    assert not citation.quote_verified
    assert citation.quote == SOURCES[1].chunk.text
    assert report.repaired_quotes == 1


def test_duplicate_citations_to_same_source_are_collapsed() -> None:
    report = validate_citations(
        [
            ModelCitation(source_id="S1", quote="5 días hábiles"),
            ModelCitation(source_id="S1", quote="plazo máximo"),
        ],
        SOURCES,
    )
    assert len(report.citations) == 1
