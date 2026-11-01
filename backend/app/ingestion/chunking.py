"""Page-bounded, sentence-aware chunking.

Chunks never span two pages so that every citation points to exactly one page. Within a page,
sentences are packed greedily up to ``max_chars``; the trailing sentences of a chunk (up to
``overlap_chars``) are repeated at the start of the next one to keep rules that span a sentence
boundary retrievable.
"""

import re
from dataclasses import dataclass

from app.ingestion.pdf import PageText

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?;:])\s+")
_SPACES = re.compile(r"[ \t]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    page: int
    text: str


def normalize_page_text(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return _SPACES.sub(" ", text).strip()


def _split_long(sentence: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for word in sentence.split(" "):
        if current and len(current) + 1 + len(word) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def _sentences(text: str, max_chars: int) -> list[str]:
    sentences: list[str] = []
    for sentence in _SENTENCE_BOUNDARY.split(text):
        sentence = sentence.strip()
        if sentence:
            sentences.extend(_split_long(sentence, max_chars))
    return sentences


def _overlap_tail(sentences: list[str], overlap_chars: int) -> list[str]:
    tail: list[str] = []
    size = 0
    for sentence in reversed(sentences):
        if size + len(sentence) > overlap_chars:
            break
        tail.insert(0, sentence)
        size += len(sentence) + 1
    return tail


def chunk_page(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    sentences = _sentences(normalize_page_text(text), max_chars)
    chunks: list[str] = []
    current: list[str] = []
    fresh = 0
    for sentence in sentences:
        candidate_len = sum(len(s) + 1 for s in current) + len(sentence)
        if current and candidate_len > max_chars:
            chunks.append(" ".join(current))
            current = _overlap_tail(current, overlap_chars)
            if sum(len(s) + 1 for s in current) + len(sentence) > max_chars:
                current = []
            fresh = 0
        current.append(sentence)
        fresh += 1
    if current and fresh:
        chunks.append(" ".join(current))
    return chunks


def chunk_pages(pages: list[PageText], max_chars: int, overlap_chars: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for text in chunk_page(page.text, max_chars, overlap_chars):
            chunks.append(Chunk(ordinal=len(chunks), page=page.page, text=text))
    return chunks
