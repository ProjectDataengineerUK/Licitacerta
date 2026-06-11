-- PERSISTENCIA_STORES: watch configs + dedup de editais vistos (PORTAL_INTEGRATION)
CREATE TABLE IF NOT EXISTS watch_configs (
    id         TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS watch_seen (
    pncp_id    TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
