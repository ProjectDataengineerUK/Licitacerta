-- Migration 011: Mentor conversational history
-- Run date: 2026-06-09

CREATE TABLE IF NOT EXISTS mentor_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL,
    tenant_id   UUID NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_mentor UNIQUE (run_id)
);

CREATE TABLE IF NOT EXISTS mentor_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES mentor_conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    tipo_resposta   VARCHAR(30),
    acoes_sugeridas JSONB DEFAULT '[]',
    evidencias      JSONB DEFAULT '[]',
    disclaimer      TEXT,
    tokens_used     INTEGER,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mm_conv ON mentor_messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mm_tenant_date ON mentor_messages(conversation_id, (created_at::date));
CREATE INDEX IF NOT EXISTS idx_mentor_conv_tenant ON mentor_conversations(tenant_id, created_at DESC);
