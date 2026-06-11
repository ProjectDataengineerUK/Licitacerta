-- Migration 010: Recebiveis antecipacao solicitacoes
-- Run date: 2026-06-09

CREATE TABLE IF NOT EXISTS recebiveis_solicitacoes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL,
    run_id            UUID,
    valor_bruto_brl   DECIMAL(15,2) NOT NULL,
    prazo_dias        INTEGER NOT NULL,
    taxa_mensal_pct   FLOAT,
    valor_liquido_brl DECIMAL(15,2),
    status            VARCHAR(20) DEFAULT 'simulado',
    aceite_termos     BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recv_tenant ON recebiveis_solicitacoes(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recv_run ON recebiveis_solicitacoes(run_id) WHERE run_id IS NOT NULL;
