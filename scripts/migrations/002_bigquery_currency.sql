-- Migration 002: add currency column to agent_runs
-- BigQuery supports ALTER TABLE ADD COLUMN IF NOT EXISTS
-- Run once per environment: bq query --use_legacy_sql=false < 002_bigquery_currency.sql

ALTER TABLE `${GCP_PROJECT_ID}.analytics.agent_runs`
ADD COLUMN IF NOT EXISTS currency STRING OPTIONS (description = 'Cost currency code (BRL or USD)');
