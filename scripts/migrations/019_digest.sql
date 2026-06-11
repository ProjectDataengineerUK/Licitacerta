-- scripts/migrations/019_digest.sql
-- Feature DIGEST_DIARIO — preferências por tenant + log de envios (idempotente).

CREATE TABLE IF NOT EXISTS digest_config (
    tenant_id      TEXT PRIMARY KEY,
    ufs            TEXT[]        NOT NULL DEFAULT '{}',
    cnaes          TEXT[]        NOT NULL DEFAULT '{}',
    valor_min      DECIMAL(18,2),
    valor_max      DECIMAL(18,2),
    palavras_chave TEXT[]        NOT NULL DEFAULT '{}',
    ativo          BOOLEAN       NOT NULL DEFAULT TRUE,
    canal_email    BOOLEAN       NOT NULL DEFAULT TRUE,
    canal_push     BOOLEAN       NOT NULL DEFAULT FALSE,
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS digest_log (
    id             UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      TEXT          NOT NULL,
    digest_date    DATE          NOT NULL,
    itens_enviados INT           NOT NULL DEFAULT 0,
    abriu_email    BOOLEAN       NOT NULL DEFAULT FALSE,
    clicks         INT           NOT NULL DEFAULT 0,
    enviado_em     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_digest_tenant_date UNIQUE (tenant_id, digest_date)
);

CREATE INDEX IF NOT EXISTS idx_digest_log_tenant_date
    ON digest_log (tenant_id, digest_date DESC);

CREATE INDEX IF NOT EXISTS idx_digest_config_ativo
    ON digest_config (tenant_id) WHERE ativo = TRUE;
