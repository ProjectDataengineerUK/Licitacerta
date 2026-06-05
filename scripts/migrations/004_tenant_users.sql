-- PAINEL_USUARIO: membros de equipe, convites e preferências de notificação por tenant
-- tenant_id é TEXT (pode ser Firebase UID ou UUID string) — sem FK para tenants

CREATE TABLE IF NOT EXISTS tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    user_uid TEXT NOT NULL,
    email TEXT NOT NULL,
    nome TEXT,
    papel TEXT CHECK (papel IN ('admin', 'analista', 'visualizador')) NOT NULL DEFAULT 'analista',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    invited_by UUID REFERENCES tenant_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, user_uid)
);

CREATE TABLE IF NOT EXISTS tenant_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    papel TEXT CHECK (papel IN ('admin', 'analista', 'visualizador')) NOT NULL DEFAULT 'analista',
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_by UUID REFERENCES tenant_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 1 row por tenant — upsert-friendly
CREATE TABLE IF NOT EXISTS notif_prefs (
    tenant_id TEXT PRIMARY KEY,
    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    whatsapp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    whatsapp_number TEXT,
    tipos_habilitados TEXT[] NOT NULL DEFAULT ARRAY[
        'vencimento_certidao', 'prazo_impugnacao', 'analise_concluida'
    ],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant  ON tenant_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_uid     ON tenant_users(user_uid);
CREATE INDEX IF NOT EXISTS idx_tenant_invites_token  ON tenant_invites(token);
CREATE INDEX IF NOT EXISTS idx_tenant_invites_tenant ON tenant_invites(tenant_id);
