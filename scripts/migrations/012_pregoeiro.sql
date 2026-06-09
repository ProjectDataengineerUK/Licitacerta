-- Migration 012: pregoeiro_profiles — weekly-computed reputation index

CREATE TABLE IF NOT EXISTS pregoeiro_profiles (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                            VARCHAR(255) NOT NULL,
    nome_normalizado                VARCHAR(255) NOT NULL,
    orgao_cnpj                      VARCHAR(14) NOT NULL,
    orgao_nome                      VARCHAR(255),
    total_sessoes                   INTEGER DEFAULT 0,
    indice_reputacao                FLOAT,
    confianca_pct                   FLOAT DEFAULT 0,
    taxa_aceitacao_impugnacao_pct   FLOAT,
    taxa_desclassificacao_pct       FLOAT,
    tempo_medio_sessao_horas        FLOAT,
    previsibilidade                 FLOAT,
    clausulas_frequentes            JSONB DEFAULT '[]',
    tipos_desclassificacao          JSONB DEFAULT '[]',
    empresas_frequentes_vencedoras  JSONB DEFAULT '[]',
    ultima_atualizacao              TIMESTAMPTZ,
    created_at                      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_pregoeiro UNIQUE (nome_normalizado, orgao_cnpj)
);

CREATE INDEX IF NOT EXISTS idx_pp_orgao ON pregoeiro_profiles (orgao_cnpj);
CREATE INDEX IF NOT EXISTS idx_pp_nome  ON pregoeiro_profiles (nome_normalizado);
