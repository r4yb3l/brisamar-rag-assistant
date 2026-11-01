CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_key        text        NOT NULL,
    title          text        NOT NULL,
    business_line  text        NOT NULL CHECK (business_line IN ('autos', 'hogar', 'vida')),
    version        integer     NOT NULL CHECK (version > 0),
    is_current     boolean     NOT NULL DEFAULT false,
    status         text        NOT NULL DEFAULT 'queued'
                               CHECK (status IN ('queued', 'processing', 'ready', 'failed')),
    error          text,
    file_sha256    text        NOT NULL,
    file_path      text        NOT NULL,
    page_count     integer,
    chunk_count    integer,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (business_line, doc_key, version)
);

CREATE UNIQUE INDEX documents_one_current_version
    ON documents (business_line, doc_key) WHERE is_current;
CREATE INDEX documents_line_created ON documents (business_line, created_at DESC);
CREATE INDEX documents_sha ON documents (business_line, doc_key, file_sha256);

CREATE TABLE chunks (
    id             uuid        PRIMARY KEY,
    document_id    uuid        NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    business_line  text        NOT NULL,
    ordinal        integer     NOT NULL,
    page           integer     NOT NULL CHECK (page > 0),
    text           text        NOT NULL,
    content_hash   text        NOT NULL,
    embedding      vector(768) NOT NULL,
    tsv            tsvector    GENERATED ALWAYS AS (to_tsvector('spanish', text)) STORED,
    UNIQUE (document_id, ordinal)
);

CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX chunks_line ON chunks (business_line);

CREATE TABLE embedding_cache (
    content_hash   text        NOT NULL,
    model          text        NOT NULL,
    embedding      vector(768) NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_hash, model)
);
