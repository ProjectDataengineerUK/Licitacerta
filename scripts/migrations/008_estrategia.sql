-- Migration 008: estrategia_acoes — competitive strategy checklist per run

CREATE TABLE IF NOT EXISTS estrategia_acoes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    numero              INTEGER NOT NULL,
    categoria           VARCHAR(20) NOT NULL,
    titulo              VARCHAR(255),
    descricao           TEXT,
    prazo               VARCHAR(50),
    impacto_pct         FLOAT,
    acao_direta_label   VARCHAR(100),
    acao_direta_rota    VARCHAR(200),
    concluida           BOOLEAN DEFAULT FALSE,
    concluida_em        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_ea UNIQUE (run_id, numero)
);

CREATE INDEX IF NOT EXISTS idx_ea_run ON estrategia_acoes (run_id);
CREATE INDEX IF NOT EXISTS idx_ea_tenant ON estrategia_acoes (tenant_id);
