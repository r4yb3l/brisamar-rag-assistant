# Decisions

Short records of the decisions that shape the system, why they were made, and what they cost.

## 1. PDF extraction: pypdf instead of Docling

Docling gives better layout (tables, reading order) but pulls PyTorch and layout models: a
multi-GB image, slow cold starts and a GPU/CPU budget that this MVP does not need for text-first
procedure manuals. PyMuPDF is faster but AGPL-licensed, which is a legal question for an insurer's
internal tool. pypdf is pure Python, BSD-licensed and good enough for born-digital PDFs.

Failure handling at this stage is explicit and permanent (no retries): corrupt or unreadable
files, password-protected files, more than 300 pages, and PDFs with almost no extractable text
(scanned images) end in `failed` with a human-readable `error`. OCR is out of scope; it would be
the first thing to add (e.g. OCRmyPDF as a preprocessing step) if the real corpus has scans.

## 2. Chunking and versioning

**Chunking.** Chunks never cross a page boundary, so every citation points to exactly one page.
Within a page, text is split into sentences and packed greedily up to 700 characters; up to 150
characters of trailing sentences are repeated at the start of the next chunk so a rule that spans
two sentences stays retrievable. Very long sentences are split on word boundaries. The sizes are
small because procedure rules are short and precise, and smaller chunks make citations precise.

**Versioning: keep history.** Documents are identified by `(business_line, doc_key)`. Uploading a
new file for an existing key creates version N+1. Chunks are immutable and keyed by
`uuid5(document_id, ordinal)`, so a citation issued last month still resolves; `GET /api/chunks/{id}`
reports `is_current=false` when that version was superseded. Retrieval only searches the current,
ready version of each document.

The new version becomes current **only when its ingestion succeeds**, in the same transaction that
writes its chunks. A broken upload therefore never hides the working manual. Promotion picks the
highest *ready* version, so two versions finishing out of order cannot demote the newer one. The
version number is allocated under a transaction-scoped advisory lock per document key.

Uploading byte-identical content for the same key (same sha256) returns the existing version
instead of re-processing it; if that version had failed, it is re-queued (re-upload = retry).

## 3. Idempotent ingestion

The Celery task is safe to run more than once (`acks_late`, redelivery after a worker crash,
manual retries):

- Chunks for a version are deleted and rewritten in **one transaction** together with the status
  change to `ready` and the promotion to current. A crash halfway leaves the previous state.
- Chunk ids are deterministic, so a rerun produces the same ids.
- A task that finds the document already `ready` is a no-op.
- Transient failures (provider outages after the in-call retries, DB connection errors) are
  retried by Celery with exponential backoff (2, 4, 8 s); after the last attempt the document is
  marked `failed` with the reason. Permanent failures (bad PDF) are never retried.

The integration test `test_reingestion_is_idempotent_and_old_citations_still_resolve` reruns the
pipeline on an ingested document and checks that the chunk ids are unchanged.

Integration tests run Celery in eager mode (`CELERY_TASK_ALWAYS_EAGER=true`): the task executes
inline with the same code path but without a broker. The real broker + worker path was verified
manually with `docker compose up` (upload → worker → ready, with the trace id and request id
propagated from the API into the worker logs).

## 4. Retrieval: hybrid search fused with RRF (second stage)

Stage one runs two queries over the current versions of the user's business lines:

1. pgvector cosine search (`<=>`) over chunk embeddings, top 20.
2. PostgreSQL full-text search with the `spanish` configuration over a generated `tsvector`
   column, top 20. The question's stemmed lexemes are OR-ed (`websearch_to_tsquery` would AND
   every word of a natural-language question and almost never match).

Stage two fuses both rankings with Reciprocal Rank Fusion (`score = Σ 1/(60 + rank)`) and keeps the
top 5. Why hybrid instead of a cross-encoder reranker:

- Insurance procedures are full of exact terms (amounts, "5 días hábiles", "franquicia",
  "Unidad de Investigación de Fraude") where lexical matching is strong and embeddings are fuzzy.
- It works offline with no extra model to download, host or pay for, and adds one indexed query.
- RRF needs no score normalisation between two incomparable scales.

A reranker (e.g. a multilingual cross-encoder or an LLM rerank) is the natural next step once
there is a larger labelled eval set to prove it pays for its latency.

## 5. Indexes: HNSW and GIN

- `HNSW (embedding vector_cosine_ops)`: better recall/latency trade-off than IVFFlat, no training
  step, and it can be built on an empty table and maintained incrementally. IVFFlat needs data to
  pick its lists and degrades when the distribution drifts as new manuals arrive. HNSW's costs are
  slower builds and more memory, irrelevant at this scale.
- `GIN (tsv)` for full-text search.
- Caveat: with an approximate index, filters are applied after the index scan, so a very
  selective filter can return fewer than `k` rows. pgvector ≥ 0.8 offers
  `hnsw.iterative_scan` for that; at the current corpus size Postgres uses exact scans anyway.

## 6. Generation, structured output and citation validation

The LLM sits behind two small protocols (`ChatModel.complete`, `EmbeddingModel.embed`) with a fake
and a LiteLLM implementation each, selected by environment variables. LiteLLM gives one interface
to Gemini, OpenAI, Azure, Bedrock, Vertex or a local Ollama without changing code.

The model must return JSON matching `ModelAnswer` (`answer`, `citations[{source_id, quote}]`,
`confidence`, `insufficient_evidence`). Sources are labelled `S1..Sn` rather than with UUIDs,
because models copy short ids reliably and mangle long ones.

- Output is validated with Pydantic. On a schema error the model gets **one** repair request that
  includes the validation error; a second failure ends in a refusal (`invalid_model_output`).
- Timeouts, rate limits, connection errors and 5xx are retried with tenacity (exponential backoff,
  4 attempts, 30 s timeout per call). If the provider stays down the API returns 503 instead of
  pretending it does not know the answer.

**Citation policy** (`app/answering/citations.py`):

- A citation to a source that was not retrieved is **dropped**.
- A citation to a retrieved source whose quote is not literally in the chunk (after accent/case/
  whitespace normalisation) keeps its location (chunk, document, version, page) but the quote is
  **replaced by a real excerpt** of that chunk. The user never sees text that is not in the manual,
  and the location the model chose is still verifiable.
- Duplicate citations to one chunk are collapsed.
- If no citation survives, the answer is **refused** (`ungrounded_answer`).

## 7. Low-confidence policy and calibration

Two gates, both must pass:

1. **Retrieval evidence gate**: the best cosine similarity among the retrieved chunks must reach
   `MIN_VECTOR_SIMILARITY`. The fused RRF score is rank-based and says nothing about absolute
   relevance, so the gate uses the vector similarity. Below it the model is not even called.
2. **Model gate**: the model can declare `insufficient_evidence`.

The reported `confidence` is `min(model confidence, top similarity)`: an answer cannot be more
confident than its evidence.

The threshold depends on the embedding model, so each provider has a default and the env var
overrides it. Calibration uses the eval: `python -m eval.run_eval` prints the top similarity of
every in-scope and out-of-scope question. With the fake embeddings the in-scope minimum was 0.194
and the out-of-scope maximum 0.000; the initial guess of 0.25 rejected 2 of 12 answerable
questions, so the default was lowered to 0.15. For Gemini embeddings unrelated texts typically
still score ~0.4–0.6, so 0.6 is a starting point that must be recalibrated the same way (pick the
value that keeps in-scope recall while refusing the out-of-scope set, and grow that set with real
analyst questions).

## 8. Authorization scope: application filter + Row Level Security

Every query filters `business_line = ANY(:user_lines)` explicitly, and the database enforces the
same rule with RLS:

- The API and worker connect as `brisamar_app`, a non-superuser role without `BYPASSRLS` that does
  not own the tables (migrations run as the admin role). RLS is also `FORCE`d.
- Each request runs in a transaction that sets `app.business_lines` with
  `set_config(..., true)` (the function form of `SET LOCAL`), so the scope dies with the
  transaction and cannot leak between pooled connections.
- Policies on `documents` and `chunks` allow rows whose `business_line` is in that list. Without
  the setting, nothing is visible (tested).

Why both: the WHERE clause keeps queries index-friendly and readable; RLS is the safety net that
turns a forgotten filter in a future query into an empty result instead of a data leak. The
`business_line` is denormalised onto `chunks` so the policy does not need a join.

Users see `404` (not `403`) for documents or chunks of other lines, so ids do not reveal existence.
The worker receives the business line in the task arguments and works under the same RLS scope.

The `embedding_cache` table is not tenant-scoped: it is keyed by the sha256 of the text, so a user
cannot look up content they do not already have. It is acceptable here; with stricter tenancy
requirements it would get a `business_line` column and the same policy.

## 9. Performance and cost

- Embeddings are cached by `(sha256(chunk text), model)`. Version 2 of a manual only embeds the
  chunks that changed; unchanged chunks reuse version 1's vectors.
- Byte-identical re-uploads are skipped entirely (file sha256 per document key).
- Files are stored content-addressed in a shared volume, so identical uploads share one file.
- Only the top 5 chunks (≈3.5k characters) are sent to the LLM.

## 10. Security

- No secrets in the repo; `.env.example` only. Database passwords and the Gemini key come from env.
- Uploads: read in 1 MB blocks with a hard 20 MB cap (413), content type checked by `%PDF-` magic
  bytes rather than extension (415), page cap of 300, `doc_key` normalised to a slug.
- The API container runs as a non-root user.
- **Prompt injection mitigation**: the question and sources are sent as a JSON object, i.e. as
  data; the system prompt states that instructions inside sources must never be followed; control
  characters are stripped; chunks matching common injection phrasings ("ignora las
  instrucciones", "ahora eres", `<system>`...) are marked `suspicious_content: true` in the
  payload and logged. Limits: pattern matching is easy to evade and models can still be steered
  by cleverly written content. The real protection is structural: the model has no tools and no
  write access, every citation is validated against retrieved text, and analysts see the cited
  passage. Stronger options: a classifier on ingested chunks, quarantining flagged documents for
  review, and restricting uploads to trusted roles.

## 11. Observability

- OpenTelemetry traces with FastAPI, Celery and psycopg instrumentation plus manual spans:
  `retrieval.hybrid` (candidate counts, top similarity), `embedding.embed` (model, input count,
  latency), `embedding.cache_lookup` (hits/misses), `llm.generate` (model, source count, flagged
  sources, per-attempt latency and token usage, whether repair happened), `ingestion.extract`,
  `ingestion.chunk`, `ingestion.store`.
- The trace context crosses the queue: the upload request and the worker's ingestion share one
  trace id. `AskOut.trace_id` lets a user report a precise trace.
- Structured JSON logs carry `request_id`, `trace_id` and `span_id`. The request id comes from
  `X-Request-ID` (or is generated), is returned in the response, and travels to the worker in a
  Celery message header.
- Exporter: console by default, OTLP/HTTP via env, Jaeger under a compose profile.

## 12. Model and provider choice, and privacy

Default: Gemini 2.5 Flash (generation) and `gemini-embedding-001` at 768 dimensions, via LiteLLM.
Flash is cheap and fast and strong enough for extractive, grounded answers; 768 dimensions
(Matryoshka-truncated) halve storage and index memory relative to 1536 with a small quality loss.
One `EMBEDDING_DIM=768` is used everywhere; the column is `vector(768)`.

Privacy: claims manuals are internal, but questions may contain policyholder data (names, policy
numbers, health information in life claims). Sending them to a public API requires a data
processing agreement, an EU region, and no training on customer data (Vertex AI in an EU region
covers this better than the consumer Gemini API). Where that is not acceptable, the same
interface runs against a self-hosted model (e.g. vLLM/Ollama through LiteLLM) and local
embeddings, at the cost of quality and operating effort. Logs never include question text or
chunk text, only ids, counts and scores.

## 13. Use of AI in this submission

The code was written with Claude Code (an AI coding assistant) working under my direction and
review: I set the architecture and constraints, and reviewed the generated code. It was verified
by:

- 23 unit tests (chunking, citation validation, repair loop, fake providers, prompt safety, upload
  validation, auth scope) and 5 integration tests against a real `pgvector/pgvector:pg16`.
- The retrieval eval (numbers in the README), which also drove the threshold change in section 7.
- A manual end-to-end run with `docker compose up --build`: seed, failed uploads, an answer citing
  version 2 page 1, a cross-line chunk returning 404, an out-of-scope refusal, and the same
  trace id and request id across API and worker logs.

The real Gemini path was not run (no key in this environment); the code for it is exercised only
up to the interface boundary.

## 14. With more time

- Run and calibrate the Gemini path; add an LLM-as-judge faithfulness eval and more questions,
  including adversarial and multi-document ones.
- Better extraction: keep headings as separate lines or metadata; OCR for scans; tables.
- A reranking stage on top of the hybrid retrieval if the bigger eval shows it helps.
- Real authentication (OIDC) with business lines from group claims.
- Alembic migrations, document deletion/archival, a dead-letter view for failed ingestions.
- Metrics (request latency, refusal rate, token spend) alongside traces.
