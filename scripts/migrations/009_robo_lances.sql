-- Migration 009: Robo de lances — tender_sessions + session_lances
-- Run date: 2026-06-09

CREATE TABLE IF NOT EXISTS tender_sessions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID NOT NULL,
    tenant_id        UUID NOT NULL,
    configuracao     JSONB NOT NULL,
    status           VARCHAR(30) NOT NULL DEFAULT 'pendente',
    job_id           VARCHAR(255),
    iniciada_em      TIMESTAMPTZ,
    encerrada_em     TIMESTAMPTZ,
    posicao_final    INTEGER,
    valor_final_brl  DECIMAL(15,2),
    motivo_encerramento TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_lances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES tender_sessions(id) ON DELETE CASCADE,
    numero              INTEGER NOT NULL,
    valor_brl           DECIMAL(15,2) NOT NULL,
    posicao_resultante  INTEGER,
    motivo              VARCHAR(20) DEFAULT 'estrategia',
    aprovado_hitl       BOOLEAN DEFAULT FALSE,
    timestamp_utc       TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ts_run ON tender_sessions(run_id);
CREATE INDEX IF NOT EXISTS idx_ts_tenant ON tender_sessions(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sl_session ON session_lances(session_id, numero);
