CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS market_contracts (
    id                   UUID DEFAULT gen_random_uuid(),
    numero_controle      VARCHAR(60) NOT NULL,
    orgao_cnpj           VARCHAR(14) NOT NULL,
    orgao_nome           VARCHAR(255),
    uasg                 VARCHAR(20),
    fornecedor_cnpj      VARCHAR(14) NOT NULL,
    fornecedor_nome      VARCHAR(255),
    objeto               TEXT,
    segmento_cnae        VARCHAR(10),
    modalidade           INTEGER,
    valor_global         DECIMAL(15,2),
    data_contrato        DATE NOT NULL,
    data_adjudicacao     DATE,
    prazo_pagamento_dias INTEGER,
    raw_data             JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, data_contrato),
    CONSTRAINT uq_market_contracts UNIQUE (numero_controle, data_contrato)
) PARTITION BY RANGE (data_contrato);

CREATE TABLE IF NOT EXISTS market_contracts_default
    PARTITION OF market_contracts DEFAULT;

CREATE INDEX IF NOT EXISTS idx_mc_fornecedor ON market_contracts(fornecedor_cnpj);
CREATE INDEX IF NOT EXISTS idx_mc_orgao      ON market_contracts(orgao_cnpj);
CREATE INDEX IF NOT EXISTS idx_mc_segmento   ON market_contracts(segmento_cnae);
CREATE INDEX IF NOT EXISTS idx_mc_data       ON market_contracts(data_contrato);

CREATE TABLE IF NOT EXISTS market_items (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contrato_numero       VARCHAR(60) NOT NULL,
    item_id               VARCHAR(60) NOT NULL,
    orgao_cnpj            VARCHAR(14) NOT NULL,
    fornecedor_cnpj       VARCHAR(14) NOT NULL,
    descricao             TEXT NOT NULL,
    descricao_normalizada TEXT NOT NULL,
    catmat_code           VARCHAR(20),
    quantidade            DECIMAL(15,4),
    valor_unitario        DECIMAL(15,4),
    segmento_cnae         VARCHAR(10),
    data_contrato         DATE NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_market_items UNIQUE (contrato_numero, item_id)
);

CREATE INDEX IF NOT EXISTS idx_mi_catmat    ON market_items(catmat_code) WHERE catmat_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mi_desc_trgm ON market_items USING GIN (descricao_normalizada gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_mi_orgao     ON market_items(orgao_cnpj);
CREATE INDEX IF NOT EXISTS idx_mi_data      ON market_items(data_contrato);
