"""Cloud Run Job: outcome recording worker.

Receives analysis outcome events from Pub/Sub and writes final
bid/no-bid decisions to BigQuery for analytics.
"""
from __future__ import annotations

import json
import os


def handle(payload: dict) -> None:
    from src.gcp.bigquery import BigQueryWriter

    writer = BigQueryWriter.from_env()
    writer.insert_outcome(
        tender_id=payload["tender_id"],
        tenant_id=payload["tenant_id"],
        pncp_id=payload.get("pncp_id", ""),
        result=payload.get("result", "unknown"),
        price_winner=payload.get("price_winner"),
        margin_pct=payload.get("margin_pct"),
        reason_disqualified=payload.get("reason_disqualified"),
    )


if __name__ == "__main__":
    raw = os.environ.get("PAYLOAD_JSON", "{}")
    handle(json.loads(raw))
