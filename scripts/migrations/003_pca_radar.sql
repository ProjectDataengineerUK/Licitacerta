-- Migration 003: PCA Radar — plano de contratações anual + previsões
-- Idempotent — safe to run multiple times

CREATE TABLE IF NOT EXISTS pca_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orgao_cnpj VARCHAR(14) NOT NULL,
    orgao_nome VARCHAR(255),
    ano INTEGER NOT NULL,
    numero_item VARCHAR(50),
    descricao TEXT NOT NULL,
    valor_estimado_brl DECIMAL(15,2),
    periodo_inicio DATE,
    periodo_fim DATE,
    categoria VARCHAR(20),
    segmento_cnae VARCHAR(10),
    status VARCHAR(20) NOT NULL DEFAULT 'planejado',
    edital_id VARCHAR(100),
    raw_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_pca_items UNIQUE (orgao_cnpj, ano, numero_item)
);

CREATE INDEX IF NOT EXISTS idx_pca_items_orgao ON pca_items(orgao_cnpj);
CREATE INDEX IF NOT EXISTS idx_pca_items_segmento ON pca_items(segmento_cnae);
CREATE INDEX IF NOT EXISTS idx_pca_items_periodo ON pca_items(periodo_inicio) WHERE status = 'planejado';

CREATE TABLE IF NOT EXISTS procurement_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    orgao_cnpj VARCHAR(14),
    orgao_nome VARCHAR(255),
    objeto_previsto TEXT,
    valor_estimado_brl DECIMAL(15,2),
    data_prevista_publicacao DATE NOT NULL,
    data_prevista_sessao DATE,
    confianca_pct FLOAT NOT NULL DEFAULT 0,
    fonte VARCHAR(20) NOT NULL DEFAULT 'pca',
    pca_item_id UUID REFERENCES pca_items(id) ON DELETE SET NULL,
    alerta_enviado BOOLEAN NOT NULL DEFAULT FALSE,
    edital_publicado_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prediction UNIQUE (tenant_id, pca_item_id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_tenant ON procurement_predictions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_predictions_alerta ON procurement_predictions(alerta_enviado, confianca_pct, data_prevista_publicacao);
CREATE INDEX IF NOT EXISTS idx_predictions_orgao ON procurement_predictions(orgao_cnpj) WHERE edital_publicado_id IS NULL;

ALTER TABLE procurement_predictions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pred_tenant_isolation ON procurement_predictions;
CREATE POLICY pred_tenant_isolation ON procurement_predictions
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));
