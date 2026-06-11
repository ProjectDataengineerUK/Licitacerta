-- scripts/migrations/015_certidoes.sql
-- Schema novo (DEFINE). Substitui schema legado de `certidoes` (valid_until/gcs_path).

CREATE TABLE IF NOT EXISTS certidoes (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     TEXT         NOT NULL,
    cnpj          TEXT         NOT NULL,
    tipo          VARCHAR(30)  NOT NULL,
    validade      DATE,
    status        VARCHAR(20)  NOT NULL DEFAULT 'nao_verificada',
    url_documento TEXT,
    verificado_em TIMESTAMPTZ,
    ultimo_alerta DATE,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- Migração defensiva do schema legado (caso a tabela já exista com colunas antigas).
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS cnpj          TEXT;
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS validade      DATE;
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS url_documento TEXT;
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS verificado_em TIMESTAMPTZ;
ALTER TABLE certidoes ADD COLUMN IF NOT EXISTS ultimo_alerta DATE;

-- Backfill do schema legado → novo (best effort).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'certidoes' AND column_name = 'valid_until') THEN
        UPDATE certidoes SET validade = valid_until WHERE validade IS NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'certidoes' AND column_name = 'gcs_path') THEN
        UPDATE certidoes SET url_documento = gcs_path WHERE url_documento IS NULL;
    END IF;
    -- Normaliza status legado (EN) → novo (PT-BR).
    UPDATE certidoes SET status = 'nao_verificada'
        WHERE status IN ('pending_review', 'pending') OR status IS NULL;
    UPDATE certidoes SET status = 'valida'        WHERE status = 'valid';
    UPDATE certidoes SET status = 'vencida'       WHERE status = 'expired';
    UPDATE certidoes SET status = 'vence_em_breve' WHERE status = 'expiring_soon';
END $$;

-- Constraints de domínio.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_certidoes_tipo') THEN
        ALTER TABLE certidoes ADD CONSTRAINT chk_certidoes_tipo
            CHECK (tipo IN ('CND_FEDERAL','FGTS','TRABALHISTA','ESTADUAL_SEFAZ','MUNICIPAL_ISSQN'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_certidoes_status') THEN
        ALTER TABLE certidoes ADD CONSTRAINT chk_certidoes_status
            CHECK (status IN ('valida','vencida','vence_em_breve','nao_verificada'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_certidoes_tenant   ON certidoes (tenant_id);
CREATE INDEX IF NOT EXISTS idx_certidoes_validade ON certidoes (status, validade)
    WHERE status IN ('valida','vence_em_breve');
CREATE UNIQUE INDEX IF NOT EXISTS uq_certidoes_tenant_cnpj_tipo
    ON certidoes (tenant_id, cnpj, tipo);
