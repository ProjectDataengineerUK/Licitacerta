-- Migration 001: juridical chunks vector store
-- Idempotent — safe to run multiple times

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS juridical_chunks (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo       TEXT        NOT NULL,   -- 'acordao' | 'sumula' | 'lei' | 'artigo'
    numero     TEXT        NOT NULL,   -- ex: '2500/2015-Plenario', 'Art. 41 §1°'
    fonte      TEXT        NOT NULL,   -- ex: 'TCU', 'Lei 14.133/2021'
    texto      TEXT        NOT NULL,   -- chunk textual
    embedding  vector(768) NOT NULL,   -- Vertex AI text-multilingual-embedding-002
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ivfflat index for approximate nearest neighbor search (cosine similarity)
-- lists=100 is appropriate for up to ~1M rows; rebuild with higher lists if needed
CREATE INDEX IF NOT EXISTS idx_juridical_chunks_embedding
    ON juridical_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
