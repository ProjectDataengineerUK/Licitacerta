-- PERSISTENCIA_STORES: alertas unificados + preferências (NOTIFICACOES_MULTICANAL)
CREATE TABLE IF NOT EXISTS alerts (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    lido       BOOLEAN NOT NULL DEFAULT FALSE,
    severidade TEXT NOT NULL DEFAULT 'info',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    data       JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_tenant_created ON alerts (tenant_id, created_at DESC);
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS alerts_tenant_isolation ON alerts;
CREATE POLICY alerts_tenant_isolation ON alerts
    USING (tenant_id = current_setting('app.tenant_id', true));
CREATE TABLE IF NOT EXISTS notification_prefs (
    tenant_id  TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
