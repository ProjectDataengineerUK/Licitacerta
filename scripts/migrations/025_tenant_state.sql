-- PERSISTENCIA_STORES: bloqueio de tenant + impersonation (PAINEL_ADMIN) — tabelas admin, sem RLS
CREATE TABLE IF NOT EXISTS tenant_states (
    tenant_id  TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS impersonation_tokens (
    token      TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
