# Brisamar RAG Assistant

Question answering with verifiable citations over the claims-procedure manuals of Brisamar Seguros
(a fictional insurer). Analysts upload PDF manuals and circulars; the system ingests them in the
background into PostgreSQL + pgvector and answers questions **only** from retrieved passages, citing
document, version and page, and refusing when the evidence is not good enough.

Stack: FastAPI · Pydantic · Celery + Redis · PostgreSQL 16 + pgvector · LiteLLM (Gemini by default)
· OpenTelemetry · React frontend (`frontend/`).

The design decisions and trade-offs are in [DECISIONS.md](DECISIONS.md).

## Quick start

```bash
cp .env.example .env            # optional: defaults work offline with the fake providers
docker compose up --build       # postgres, redis, migrate, api, worker, frontend
python scripts/seed.py          # uploads the sample manuals through the API (stdlib only)
```

- Frontend: http://localhost:5173
- API docs (OpenAPI): http://localhost:8000/docs
- Demo bearer tokens: `analyst-autos` (autos), `analyst-hogar` (hogar), `analyst-all`
  (autos, hogar, vida)

`python scripts/seed.py --with-failures` also uploads a corrupt PDF and a text-less (scanned) PDF,
which end in `failed` with an explicit error.

```bash
curl -s -X POST localhost:8000/api/ask \
  -H 'Authorization: Bearer analyst-autos' -H 'Content-Type: application/json' \
  --data-binary '{"question": "¿En qué plazo debe comunicarse un siniestro de autos?"}'
```

Optional Jaeger UI: `docker compose --profile tracing up --build` with
`OTEL_EXPORTER=otlp` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318` in `.env`, then open
http://localhost:16686.

## Fake vs real providers

| Variable | `fake` (default) | `litellm` |
|---|---|---|
| `EMBEDDING_PROVIDER` | Deterministic hashed bag-of-words (768 dims), offline | `gemini/gemini-embedding-001`, 768 dims |
| `LLM_PROVIDER` | Extractive: picks the sentences that best overlap the question and cites them | `gemini/gemini-2.5-flash`, JSON output |

The fake providers exercise the same prompt, schema validation, citation validation and refusal
path as the real ones; they exist so that tests, CI and the demo run without network or keys.
To use Gemini set `LLM_PROVIDER=litellm`, `EMBEDDING_PROVIDER=litellm` and `GEMINI_API_KEY`.
Any LiteLLM model string works (`LLM_MODEL`, `EMBEDDING_MODEL`). Embeddings from different models
are not comparable: after switching the embedding provider, re-ingest (start from an empty
volume) and recalibrate `MIN_VECTOR_SIMILARITY` with the eval.

## Tests and eval

```bash
bash scripts/test.sh     # or: make test
```

Runs ruff, the unit tests, the integration tests against a real pgvector Postgres (it starts a
throwaway `pgvector/pgvector:pg16` container when `DATABASE_URL` is not set) and the retrieval
eval. Without Docker and without `DATABASE_URL`, integration tests are skipped and only unit tests
run. CI (`.github/workflows/ci.yml`) runs the same steps against Postgres and Redis service
containers and builds the backend image.

Local setup for running the suite outside Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -c requirements.lock -e ".[dev]"
```

Latest local results (fake providers):

- 23 unit tests + 5 integration tests: 28 passed.
- Eval, 12 in-scope questions, hit means *expected document and page*: hit@1 0.75,
  recall@5 1.00, MRR 0.875. Evidence gate: 12/12 in-scope answered, 3/3 out-of-scope refused.

## API

All endpoints are under `/api` and require `Authorization: Bearer <demo-token>` except health.

| Method | Path | Notes |
|---|---|---|
| `POST` | `/documents` | multipart `file`, `business_line`, optional `doc_key`, `title` → 202 |
| `GET` | `/documents?business_line=` | `{"items": [...]}` newest first |
| `GET` | `/documents/{id}` | ingestion status (`queued`, `processing`, `ready`, `failed`) |
| `POST` | `/ask` | `{"question", "business_line"}` → answer, citations, confidence |
| `GET` | `/chunks/{id}` | cited passage; `is_current=false` when that version was superseded |
| `GET` | `/health` | no auth |

`refusal_reason` values: `no_relevant_evidence` (retrieval below the evidence threshold),
`model_insufficient_evidence` (the model said the sources do not answer), `ungrounded_answer`
(no citation survived validation), `invalid_model_output` (schema broken twice). Provider outages
after retries return 503.

Upload errors: 401 bad token, 403 business line not allowed, 413 over 20 MB, 415 not a PDF
(checked by magic bytes), 422 invalid fields.

## Layout

```
backend/
  app/
    api/            routes and response schemas (the frontend contract)
    answering/      ask orchestration, generator with repair retry, citation validation
    core/           settings, demo-token auth
    db/             migrations runner, RLS-scoped transactions, document repository
    ingestion/      PDF extraction, chunking, embedding cache, pipeline, upload validation
    llm/            chat + embedding providers (fake / LiteLLM), prompt, output schema
    observability/  JSON logging with request id, OpenTelemetry setup
    retrieval/      hybrid search (pgvector + full-text, RRF)
    main.py, worker.py
  migrations/       plain SQL (schema, RLS policies)
  tests/unit, tests/integration
  eval/             questions.json + run_eval.py
frontend/           React UI
samples/            synthetic PDFs (generated by scripts/generate_samples.py)
scripts/            generate_samples.py, seed.py, test.sh
```

## Status

Done: everything in the brief's MVP and quality list, with the choices explained in DECISIONS.md.

Not done / known limits:

- No OCR: scanned PDFs are rejected with an explicit error instead of being OCR'd.
- Authentication is simulated with fixed demo tokens.
- Headings are merged into the first sentence of their section by the PDF text extraction
  (visible in fake answers such as "Declaración del siniestro El asegurado...").
- The real Gemini path is implemented but was not exercised in this submission (no API key in the
  environment); its evidence threshold (0.6) is a starting value that must be calibrated.
- No document deletion endpoint and no admin UI for re-processing failed documents (re-uploading
  the same file re-queues it).
