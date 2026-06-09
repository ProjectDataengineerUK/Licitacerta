-- Migration 013: Coach Onboarding — dicas + progresso por tenant

CREATE TABLE IF NOT EXISTS coach_dicas (
    id            VARCHAR(80) PRIMARY KEY,
    titulo        VARCHAR(200) NOT NULL,
    descricao     TEXT NOT NULL,
    categoria     VARCHAR(30) NOT NULL,
    rota_sugerida VARCHAR(200),
    ordem         INTEGER NOT NULL DEFAULT 0,
    ativo         BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS onboarding_progresso (
    tenant_id      UUID NOT NULL,
    dica_id        VARCHAR(80) NOT NULL REFERENCES coach_dicas(id),
    visto_em       TIMESTAMPTZ,
    dispensado_em  TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, dica_id)
);

CREATE INDEX IF NOT EXISTS idx_ob_tenant ON onboarding_progresso(tenant_id);
