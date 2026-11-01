"""Retrieval eval: ingests the sample manuals and reports hit@k / MRR plus the refusal gate.

    python -m eval.run_eval

A hit is the first retrieved chunk from the expected document *and* page, so the metric also
measures citation precision, not just document routing.
"""

import json
import logging
import sys
import uuid
from pathlib import Path
from statistics import mean

from app.answering.service import min_similarity, retrieve, top_similarity
from app.core.config import BUSINESS_LINES, get_settings
from app.db import documents as repo
from app.db.migrate import run_migrations
from app.db.session import scoped_transaction
from app.ingestion.pipeline import ingest_document
from app.ingestion.uploads import store_file
from app.llm.embeddings import get_embedding_model

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = Path(__file__).with_name("questions.json")
CORPUS = [
    ("manual-siniestros-autos-v1.pdf", "autos", "manual-siniestros-autos"),
    ("manual-siniestros-autos-v2.pdf", "autos", "manual-siniestros-autos"),
    ("circular-antifraude-autos.pdf", "autos", "circular-antifraude-autos"),
    ("manual-siniestros-hogar.pdf", "hogar", "manual-siniestros-hogar"),
    ("circular-prestaciones-vida.pdf", "vida", "circular-prestaciones-vida"),
]


def ingest_corpus() -> None:
    settings = get_settings()
    embedder = get_embedding_model(settings)
    for filename, line, doc_key in CORPUS:
        sha256, path = store_file((ROOT / "samples" / filename).read_bytes(), settings.upload_dir)
        with scoped_transaction([line]) as conn:
            registered = repo.register_upload(
                conn,
                doc_key=doc_key,
                title=doc_key,
                business_line=line,
                file_sha256=sha256,
                file_path=str(path),
            )
        if registered.needs_ingestion:
            ingest_document(uuid.UUID(str(registered.row["id"])), line, embedder, settings)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.WARNING)
    settings = get_settings()
    embedder = get_embedding_model(settings)
    run_migrations()
    ingest_corpus()
    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    threshold = min_similarity(settings, embedder)
    k = settings.retrieval_top_k

    print(f"embedding model: {embedder.name} | top_k={k} | evidence threshold={threshold}")
    reciprocal_ranks: list[float] = []
    in_scope_similarities: list[float] = []
    for case in cases["in_scope"]:
        chunks = retrieve(case["question"], BUSINESS_LINES, embedder, settings)
        rank = next(
            (
                position
                for position, chunk in enumerate(chunks, start=1)
                if chunk.doc_key == case["doc_key"] and chunk.page == case["page"]
            ),
            None,
        )
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        in_scope_similarities.append(top_similarity(chunks))
        print(
            f"  rank={rank or '-':>2}  sim={top_similarity(chunks):.3f}  "
            f"{case['doc_key']} p{case['page']}  | {case['question']}"
        )

    out_scope_similarities = [
        top_similarity(retrieve(question, BUSINESS_LINES, embedder, settings))
        for question in cases["out_of_scope"]
    ]
    for question, similarity in zip(cases["out_of_scope"], out_scope_similarities, strict=True):
        print(f"  out-of-scope sim={similarity:.3f} refused={similarity < threshold} | {question}")

    total = len(reciprocal_ranks)
    print("\nResults")
    print(f"  questions        : {total} in scope, {len(out_scope_similarities)} out of scope")
    print(f"  hit@1            : {sum(rr == 1 for rr in reciprocal_ranks) / total:.2f}")
    print(f"  recall@{k}         : {sum(rr > 0 for rr in reciprocal_ranks) / total:.2f}")
    print(f"  MRR              : {mean(reciprocal_ranks):.3f}")
    answered = sum(similarity >= threshold for similarity in in_scope_similarities)
    refused = sum(similarity < threshold for similarity in out_scope_similarities)
    print(f"  in-scope passing evidence gate : {answered}/{total}")
    print(f"  out-of-scope refused by gate   : {refused}/{len(out_scope_similarities)}")
    print(
        f"  similarity range: in-scope min={min(in_scope_similarities):.3f}, "
        f"out-of-scope max={max(out_scope_similarities):.3f}"
    )


if __name__ == "__main__":
    main()
