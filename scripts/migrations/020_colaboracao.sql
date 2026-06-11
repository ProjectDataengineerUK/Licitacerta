-- scripts/migrations/020_colaboracao.sql
-- IMPORTANTE: run_id é TEXT (RunStore in-memory). NUNCA criar FK para run_id.

CREATE TABLE IF NOT EXISTS run_comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      TEXT NOT NULL,
    tenant_id   TEXT NOT NULL,
    user_uid    TEXT NOT NULL,
    texto       TEXT NOT NULL CHECK (char_length(texto) <= 4000),
    mencoes     TEXT[] NOT NULL DEFAULT '{}',
    deleted_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS run_approval_status (
    run_id          TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'rascunho'
                    CHECK (status IN ('rascunho','em_revisao','aprovado','submetido')),
    atualizado_por  TEXT NOT NULL,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS run_status_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    status_anterior VARCHAR(20),
    status_novo     VARCHAR(20) NOT NULL,
    atualizado_por  TEXT NOT NULL,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_comments_run
    ON run_comments (tenant_id, run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_run_approval_tenant
    ON run_approval_status (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_run_status_history_run
    ON run_status_history (tenant_id, run_id, atualizado_em);
