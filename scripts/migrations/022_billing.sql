-- PERSISTENCIA_STORES: billing por tenant
CREATE TABLE IF NOT EXISTS tenant_billing (
    tenant_id               TEXT PRIMARY KEY,
    stripe_customer_id      TEXT,
    stripe_subscription_id  TEXT,
    data                    JSONB NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_billing_sub ON tenant_billing (stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_billing_cust ON tenant_billing (stripe_customer_id);
