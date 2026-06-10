-- scripts/migrations/014_lgpd.sql
-- INVARIANTE: consent_log é APPEND-ONLY — nunca UPDATE/DELETE
-- IP em claro NUNCA é persistido (somente SHA-256 CHAR(64))

CREATE TABLE IF NOT EXISTS consent_log (
    id               BIGSERIAL    PRIMARY KEY,
    user_id          TEXT         NOT NULL,
    version          VARCHAR(20)  NOT NULL,
    accepted_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ip_hash          CHAR(64)     NOT NULL,
    accepted_tou     BOOLEAN      NOT NULL,
    accepted_privacy BOOLEAN      NOT NULL,
    CONSTRAINT ck_consent_ip_hash_hex
        CHECK (ip_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_consent_user_version
    ON consent_log (user_id, version, accepted_at DESC);

CREATE TABLE IF NOT EXISTS data_deletion_requests (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           TEXT         NOT NULL,
    user_id             TEXT         NOT NULL,
    requested_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    scheduled_delete_at TIMESTAMPTZ  NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    executed_at         TIMESTAMPTZ,
    status              VARCHAR(20)  NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'executed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_deletion_tenant_status
    ON data_deletion_requests (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_deletion_due
    ON data_deletion_requests (scheduled_delete_at)
    WHERE status = 'pending';

CREATE UNIQUE INDEX IF NOT EXISTS uq_deletion_active_per_user
    ON data_deletion_requests (user_id)
    WHERE status IN ('pending', 'processing');
