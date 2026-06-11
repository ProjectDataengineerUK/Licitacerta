-- PERSISTENCIA_STORES: trilha de auditoria admin — append-only
CREATE TABLE IF NOT EXISTS admin_audit (
    id         TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    data       JSONB NOT NULL
);
REVOKE UPDATE, DELETE ON admin_audit FROM PUBLIC;
