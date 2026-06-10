-- scripts/migrations/016_exportacao.sql
-- run_id SEM FK — RunStore é in-memory; FK lógica apenas
CREATE TABLE IF NOT EXISTS proposal_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      TEXT NOT NULL,
    tenant_id   TEXT NOT NULL,
    version_num INTEGER NOT NULL,
    formato     VARCHAR(10) NOT NULL CHECK (formato IN ('docx', 'pdf')),
    gcs_path    TEXT NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_proposal_version UNIQUE (run_id, version_num, formato)
);

CREATE INDEX IF NOT EXISTS idx_pv_run_id ON proposal_versions (run_id, tenant_id);
