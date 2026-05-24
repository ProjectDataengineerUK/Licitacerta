from __future__ import annotations

import os
from datetime import datetime
from typing import Any


class BigQueryWriter:
    def __init__(self, client: Any, project: str, dataset: str) -> None:
        self._client = client
        self._project = project
        self._dataset = dataset

    @classmethod
    def from_env(cls) -> BigQueryWriter:
        from google.cloud import bigquery  # lazy import

        project = os.environ["GCP_PROJECT_ID"]
        return cls(bigquery.Client(project=project), project, "analytics")

    def _table(self, name: str) -> str:
        return f"{self._project}.{self._dataset}.{name}"

    def insert_agent_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        agent_name: str,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        cost_brl: float,
        eval_score: float | None = None,
        error: str | None = None,
    ) -> None:
        rows = [
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "agent_name": agent_name,
                "model_id": model_id,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                "cost_brl": cost_brl,
                "eval_score": eval_score,
                "error": error,
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        errors = self._client.insert_rows_json(self._table("agent_runs"), rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")

    def insert_outcome(
        self,
        *,
        tender_id: str,
        tenant_id: str,
        pncp_id: str,
        result: str,
        price_winner: float | None,
        margin_pct: float | None,
        reason_disqualified: str | None = None,
    ) -> None:
        rows = [
            {
                "tender_id": tender_id,
                "tenant_id": tenant_id,
                "pncp_id": pncp_id,
                "result": result,
                "price_winner": price_winner,
                "margin_pct": margin_pct,
                "reason_disqualified": reason_disqualified,
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        errors = self._client.insert_rows_json(self._table("outcomes"), rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")
