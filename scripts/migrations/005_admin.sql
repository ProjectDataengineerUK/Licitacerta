-- PAINEL_ADMIN: feature flags, audit log (append-only) e estado de bloqueio por tenant

CREATE TABLE IF NOT EXISTS feature_flags (
    tenant_id TEXT NOT NULL,
    feature VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    override BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    note TEXT,
    created_by VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, feature)
);

-- Audit log — append-only (sem DELETE grant para service account)
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_email VARCHAR(255) NOT NULL,
    acao VARCHAR(100) NOT NULL,
    entidade_tipo VARCHAR(50),
    entidade_id TEXT,
    dados_antes JSONB,
    dados_depois JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- REVOKE DELETE ON admin_audit_log FROM PUBLIC;

-- Estado de bloqueio por tenant
CREATE TABLE IF NOT EXISTS tenant_state (
    tenant_id TEXT PRIMARY KEY,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason TEXT,
    blocked_at TIMESTAMPTZ,
    blocked_by VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_tenant  ON feature_flags(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_admin       ON admin_audit_log(admin_email);
CREATE INDEX IF NOT EXISTS idx_audit_log_created     ON admin_audit_log(created_at DESC);
