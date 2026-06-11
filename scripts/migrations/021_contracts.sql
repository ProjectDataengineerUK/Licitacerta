-- PERSISTENCIA_STORES: contratos (GESTAO_CONTRATOS_FULL) — JSONB + colunas promovidas
CREATE TABLE IF NOT EXISTS contracts (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    status          TEXT NOT NULL DEFAULT 'ativo',
    data_inicio     DATE,
    data_vencimento DATE,
    data            JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_contracts_tenant ON contracts (tenant_id, status);
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS contracts_tenant_isolation ON contracts;
CREATE POLICY contracts_tenant_isolation ON contracts
    USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true));
