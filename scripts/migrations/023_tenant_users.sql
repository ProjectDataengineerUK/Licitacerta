-- PERSISTENCIA_STORES: membros, convites e prefs (PAINEL_USUARIO)
CREATE TABLE IF NOT EXISTS tenant_members (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_members_tenant ON tenant_members (tenant_id);
CREATE TABLE IF NOT EXISTS tenant_invites (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invites_tenant ON tenant_invites (tenant_id);
CREATE TABLE IF NOT EXISTS tenant_notif_prefs (
    tenant_id  TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
