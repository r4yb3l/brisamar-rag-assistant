"""Citation validation policy.

* A citation whose ``source_id`` was not among the retrieved sources is dropped.
* A citation to a retrieved source whose quote is not literally present in that chunk keeps
  its location (chunk, document, version, page) but the quote is replaced by a real excerpt,
  so the UI never shows text that the manual does not contain.
* Duplicate citations to the same chunk are collapsed.
* If nothing survives, the caller must refuse: an answer without grounded citations is not served.
"""

import re
from dataclasses import dataclass

from app.llm.prompt import PromptSource
from app.llm.schemas import ModelCitation
from app.llm.text import fold

EXCERPT_CHARS = 240
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class ValidatedCitation:
    source: PromptSource
    quote: str
    quote_verified: bool


@dataclass(frozen=True)
class CitationReport:
    citations: list[ValidatedCitation]
    dropped_unknown: int
    repaired_quotes: int


def _normalize(text: str) -> str:
    return _SPACES.sub(" ", fold(text)).strip(" .\"'«»")


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    compact = _SPACES.sub(" ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0] + "…"


def validate_citations(
    citations: list[ModelCitation], sources: list[PromptSource]
) -> CitationReport:
    by_id = {source.source_id: source for source in sources}
    validated: list[ValidatedCitation] = []
    seen: set[str] = set()
    dropped = repaired = 0
    for citation in citations:
        source = by_id.get(citation.source_id.strip())
        if source is None:
            dropped += 1
            continue
        if source.source_id in seen:
            continue
        seen.add(source.source_id)
        quote_found = bool(_normalize(citation.quote)) and _normalize(citation.quote) in _normalize(
            source.chunk.text
        )
        if not quote_found:
            repaired += 1
        validated.append(
            ValidatedCitation(
                source=source,
                quote=citation.quote.strip() if quote_found else excerpt(source.chunk.text),
                quote_verified=quote_found,
            )
        )
    return CitationReport(validated, dropped, repaired)
