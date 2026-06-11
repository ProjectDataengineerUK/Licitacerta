-- scripts/migrations/018_outcome.sql
-- run_id SEM FK — RunStore é in-memory; FK lógica apenas
CREATE TABLE IF NOT EXISTS run_outcomes (
    run_id          TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    resultado       VARCHAR(10) NOT NULL
                        CHECK (resultado IN ('ganhou', 'perdeu', 'desistiu')),
    preco_vencedor  DECIMAL(15,2),
    preco_proposto  DECIMAL(15,2),
    observacao      TEXT,
    outcome_insight TEXT,
    -- Denormalização: snapshot do run no momento do registro
    segmento        TEXT,
    uf              TEXT,
    modalidade      TEXT,
    faixa_valor     TEXT,
    bid_no_bid_score DECIMAL(4,3),  -- BidDecision.confidence
    registrado_em   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_run_outcomes_tenant
    ON run_outcomes (tenant_id, registrado_em DESC);
CREATE INDEX IF NOT EXISTS idx_run_outcomes_resultado
    ON run_outcomes (tenant_id, resultado);
