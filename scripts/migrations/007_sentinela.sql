-- Migration 007: Sentinela MLOps — prompt versioning + data source health

CREATE TABLE IF NOT EXISTS prompt_versions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name    VARCHAR(50)  NOT NULL,
    version       VARCHAR(20)  NOT NULL,  -- semver
    hash          VARCHAR(64)  NOT NULL,  -- SHA256 do system_prompt
    system_prompt TEXT         NOT NULL,
    author        VARCHAR(255),
    changelog     TEXT,
    eval_score    FLOAT,
    active        BOOLEAN      DEFAULT FALSE,
    deployed_at   TIMESTAMPTZ,
    rolled_back   BOOLEAN      DEFAULT FALSE,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT uq_pv UNIQUE (agent_name, version)
);

CREATE INDEX IF NOT EXISTS idx_pv_active ON prompt_versions (agent_name, active);

CREATE TABLE IF NOT EXISTS data_source_health (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name              VARCHAR(50) NOT NULL,  -- 'pncp', 'bll', 'comprasnet'
    checked_at               TIMESTAMPTZ NOT NULL,
    editais_count            INTEGER,
    campos_obrigatorios_pct  FLOAT,
    pdf_legibilidade_pct     FLOAT,
    is_fresh                 BOOLEAN,
    latency_ms               INTEGER,
    error                    TEXT
);

CREATE INDEX IF NOT EXISTS idx_dsh_source ON data_source_health (source_name, checked_at DESC);
