-- scripts/migrations/017_onboarding_ativacao.sql
CREATE TABLE IF NOT EXISTS onboarding_ativacao (
    tenant_id                  TEXT PRIMARY KEY,
    step_atual                 INT NOT NULL DEFAULT 0,
    cnpj_preenchido            BOOLEAN NOT NULL DEFAULT FALSE,
    primeiro_edital_submetido  BOOLEAN NOT NULL DEFAULT FALSE,
    analise_concluida          BOOLEAN NOT NULL DEFAULT FALSE,
    email_enviado              BOOLEAN NOT NULL DEFAULT FALSE,
    iniciado_em                TIMESTAMPTZ,
    concluido_em               TIMESTAMPTZ,
    run_id_express             TEXT,
    created_at                 TIMESTAMPTZ DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS ativado BOOLEAN NOT NULL DEFAULT FALSE;
