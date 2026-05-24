"""Unit tests for BigQueryWriter — no real GCP calls."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.gcp.bigquery import BigQueryWriter


@pytest.fixture
def writer():
    client = MagicMock()
    client.insert_rows_json.return_value = []  # empty = no errors
    return BigQueryWriter(client, "test-project", "analytics")


def test_insert_agent_run(writer):
    writer.insert_agent_run(
        run_id="run-1",
        tenant_id="tenant-1",
        agent_name="compliance",
        model_id="claude-sonnet-4-6",
        tokens_in=100,
        tokens_out=200,
        latency_ms=1500,
        cost_brl=0.05,
    )
    writer._client.insert_rows_json.assert_called_once()
    args = writer._client.insert_rows_json.call_args
    table, rows = args[0]
    assert table == "test-project.analytics.agent_runs"
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["agent_name"] == "compliance"


def test_insert_agent_run_raises_on_bq_error(writer):
    writer._client.insert_rows_json.return_value = [{"error": "quota exceeded"}]
    with pytest.raises(RuntimeError, match="BigQuery insert errors"):
        writer.insert_agent_run(
            run_id="run-2",
            tenant_id="tenant-1",
            agent_name="pricing",
            model_id="gemini-2.0-flash-001",
            tokens_in=50,
            tokens_out=80,
            latency_ms=700,
            cost_brl=0.01,
        )


def test_insert_outcome(writer):
    writer.insert_outcome(
        tender_id="tender-1",
        tenant_id="tenant-1",
        pncp_id="PNCP-001",
        result="bid",
        price_winner=50000.0,
        margin_pct=12.5,
    )
    args = writer._client.insert_rows_json.call_args
    table, rows = args[0]
    assert table == "test-project.analytics.outcomes"
    assert rows[0]["result"] == "bid"
    assert rows[0]["margin_pct"] == 12.5
