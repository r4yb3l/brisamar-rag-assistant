import os
import uuid

import psycopg

from app.core.config import get_settings
from app.ingestion.pipeline import ingest_document
from app.llm.embeddings import get_embedding_model
from tests.integration.conftest import auth

AUTOS_DEADLINE_QUESTION = "¿En qué plazo hay que comunicar el siniestro de autos?"


def test_ingest_and_ask_returns_answer_grounded_in_current_version(client, upload) -> None:
    v1 = upload("manual-siniestros-autos-v1.pdf", "autos", "manual-siniestros-autos")
    v2 = upload("manual-siniestros-autos-v2.pdf", "autos", "manual-siniestros-autos")
    upload("manual-siniestros-hogar.pdf", "hogar", "manual-siniestros-hogar")

    assert (v1["status"], v2["status"]) == ("ready", "ready")
    assert (v1["version"], v2["version"]) == (1, 2)
    assert v2["is_current"] and v2["page_count"] == 2 and v2["chunk_count"] > 0
    refreshed_v1 = client.get(f"/api/documents/{v1['id']}", headers=auth("analyst-all")).json()
    assert not refreshed_v1["is_current"]

    response = client.post(
        "/api/ask",
        headers=auth("analyst-autos"),
        json={"question": AUTOS_DEADLINE_QUESTION, "business_line": None},
    )
    assert response.status_code == 200
    body = response.json()
    assert not body["refused"], body
    assert "5 días hábiles" in body["answer"]
    assert body["citations"]
    assert 0 < body["confidence"] <= 1
    for citation in body["citations"]:
        assert citation["document_id"] == v2["id"]
        assert citation["version"] == 2
        chunk = client.get(f"/api/chunks/{citation['chunk_id']}", headers=auth("analyst-autos"))
        assert chunk.status_code == 200
        assert citation["quote"] in chunk.json()["text"]
        assert chunk.json()["page"] == citation["page"]


def test_reingestion_is_idempotent_and_old_citations_still_resolve(client, upload) -> None:
    v1 = upload("manual-siniestros-autos-v1.pdf", "autos", "manual-siniestros-autos")
    duplicate = client.post(
        "/api/documents",
        headers=auth("analyst-autos"),
        data={"business_line": "autos", "doc_key": "manual-siniestros-autos"},
        files={"file": ("again.pdf", _sample("manual-siniestros-autos-v1.pdf"), "application/pdf")},
    ).json()
    assert duplicate["id"] == v1["id"] and duplicate["version"] == 1

    chunk_ids_before = _chunk_ids(v1["id"])
    with psycopg.connect(os.environ["DATABASE_ADMIN_URL"], autocommit=True) as conn:
        conn.execute("UPDATE documents SET status = 'processing' WHERE id = %s", (v1["id"],))
    settings = get_settings()
    ingest_document(uuid.UUID(v1["id"]), "autos", get_embedding_model(settings), settings)
    assert _chunk_ids(v1["id"]) == chunk_ids_before

    upload("manual-siniestros-autos-v2.pdf", "autos", "manual-siniestros-autos")
    old_chunk = client.get(f"/api/chunks/{chunk_ids_before[0]}", headers=auth("analyst-autos"))
    assert old_chunk.status_code == 200
    assert old_chunk.json()["version"] == 1 and not old_chunk.json()["is_current"]


def test_business_line_isolation_in_api_and_database(client, upload) -> None:
    autos = upload("manual-siniestros-autos-v2.pdf", "autos", "manual-siniestros-autos")
    upload("manual-siniestros-hogar.pdf", "hogar", "manual-siniestros-hogar")

    hogar_view = client.get("/api/documents", headers=auth("analyst-hogar")).json()["items"]
    assert {item["business_line"] for item in hogar_view} == {"hogar"}
    assert (
        client.get(f"/api/documents/{autos['id']}", headers=auth("analyst-hogar")).status_code
        == 404
    )
    forbidden = client.post(
        "/api/ask",
        headers=auth("analyst-hogar"),
        json={"question": AUTOS_DEADLINE_QUESTION, "business_line": "autos"},
    )
    assert forbidden.status_code == 403
    answer = client.post(
        "/api/ask", headers=auth("analyst-hogar"), json={"question": AUTOS_DEADLINE_QUESTION}
    ).json()
    assert all(citation["document_id"] != autos["id"] for citation in answer["citations"])
    autos_chunk = _chunk_ids(autos["id"])[0]
    assert (
        client.get(f"/api/chunks/{autos_chunk}", headers=auth("analyst-hogar")).status_code == 404
    )

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.transaction():
        conn.execute("SELECT set_config('app.business_lines', 'hogar', true)")
        visible = conn.execute("SELECT DISTINCT business_line FROM chunks").fetchall()
        assert visible == [("hogar",)]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        assert conn.execute("SELECT count(*) FROM documents").fetchone() == (0,)
    assert client.get("/api/documents").status_code == 401


def test_out_of_scope_question_is_refused(client, upload) -> None:
    upload("manual-siniestros-autos-v2.pdf", "autos", "manual-siniestros-autos")
    upload("circular-prestaciones-vida.pdf", "vida", "circular-prestaciones-vida")
    body = client.post(
        "/api/ask",
        headers=auth("analyst-all"),
        json={"question": "¿Cuál es la receta tradicional de la paella valenciana?"},
    ).json()
    assert body["refused"] is True
    assert body["refusal_reason"] == "no_relevant_evidence"
    assert body["citations"] == [] and body["confidence"] == 0


def test_broken_pdfs_are_marked_failed_with_clear_error(upload) -> None:
    corrupt = upload("corrupto.pdf", "hogar", "pdf-corrupto")
    scanned = upload("escaneado-sin-texto.pdf", "vida", "pdf-escaneado")
    assert corrupt["status"] == "failed" and "corrupt" in corrupt["error"]
    assert scanned["status"] == "failed" and "no extractable text" in scanned["error"]


def _sample(name: str) -> bytes:
    from tests.integration.conftest import SAMPLES_DIR

    return (SAMPLES_DIR / name).read_bytes()


def _chunk_ids(document_id: str) -> list[str]:
    with psycopg.connect(os.environ["DATABASE_ADMIN_URL"]) as conn:
        rows = conn.execute(
            "SELECT id FROM chunks WHERE document_id = %s ORDER BY ordinal", (document_id,)
        ).fetchall()
    return [str(row[0]) for row in rows]
