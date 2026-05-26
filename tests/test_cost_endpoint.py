from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.api.models import AgentCost, RunCost
from src.api.routes.runs import _cost_from_state
from src.api.store import RunStore
from src.schemas.results import AgentMetric


def _make_metric(agent: str, subgraph: str, cost: float, tokens_in: int = 100, tokens_out: int = 50) -> AgentMetric:
    return AgentMetric(
        subgraph=subgraph, agent=agent,
        metric_name="cost_brl", value=cost,
        timestamp=datetime.utcnow(),
        tokens_in=tokens_in, tokens_out=tokens_out,
        cost_brl=cost, latency_ms=500,
    )


@pytest_asyncio.fixture()
async def client_with_store():
    store = RunStore()
    await store.create("cost-run-1", {
        "current_step": "completed",
        "metrics": [
            _make_metric("compliance", "validation", 0.05),
            _make_metric("eligibility", "validation", 0.02, tokens_in=200, tokens_out=30),
        ],
    })
    await store.create("mem-run-1", {
        "current_step": "completed",
        "metrics": [_make_metric("compliance", "validation", 0.05)],
    })

    app = create_app()
    app.state.store = store

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, store


AUTH = {"Authorization": "Bearer testtoken"}


@pytest.mark.asyncio
async def test_at004_cost_from_bigquery_returns_aggregated_data(client_with_store):
    client, _ = client_with_store
    bq_result = RunCost(
        run_id="cost-run-1",
        agents=[AgentCost(name="compliance", tokens_in=100, tokens_out=50, cost_brl=0.05)],
        total_cost_brl=0.05,
        source="bigquery",
    )
    with patch("src.api.routes.runs._try_bigquery_cost", new=AsyncMock(return_value=bq_result)):
        resp = await client.get("/runs/cost-run-1/cost", headers=AUTH)

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "bigquery"
    assert len(data["agents"]) == 1


@pytest.mark.asyncio
async def test_at004_total_cost_brl_is_sum_of_agents():
    cost = _cost_from_state("r1", {
        "metrics": [
            _make_metric("compliance", "validation", 0.05).__dict__ if False else
            {"subgraph": "v", "agent": "compliance", "metric_name": "cost_brl",
             "value": 0.0, "timestamp": "2026-01-01T00:00:00",
             "tokens_in": 100, "tokens_out": 50, "cost_brl": 0.05},
            {"subgraph": "v", "agent": "eligibility", "metric_name": "cost_brl",
             "value": 0.0, "timestamp": "2026-01-01T00:00:00",
             "tokens_in": 200, "tokens_out": 30, "cost_brl": 0.02},
        ]
    })
    assert abs(cost.total_cost_brl - 0.07) < 0.0001
    assert cost.source == "memory"


@pytest.mark.asyncio
async def test_at005_fallback_to_memory_on_bigquery_error(client_with_store):
    client, _ = client_with_store
    with patch("src.api.routes.runs._try_bigquery_cost", new=AsyncMock(return_value=None)):
        resp = await client.get("/runs/mem-run-1/cost", headers=AUTH)

    assert resp.status_code == 200
    assert resp.json()["source"] == "memory"
    assert len(resp.json()["agents"]) == 1


@pytest.mark.asyncio
async def test_at006_cost_unknown_run_returns_404(client_with_store):
    client, _ = client_with_store
    resp = await client.get("/runs/no-such-run/cost", headers=AUTH)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cost_endpoint_requires_auth(client_with_store, monkeypatch):
    monkeypatch.setenv("LICITACERTA_API_KEYS", "valid-key:user")
    import src.api.auth as _auth
    monkeypatch.setattr(_auth, "_KEY_STORE", _auth.parse_api_keys("valid-key:user"))
    client, _ = client_with_store
    resp = await client.get("/runs/cost-run-1/cost")
    assert resp.status_code in (401, 403)


def test_cost_from_state_handles_legacy_metric_format():
    cost = _cost_from_state("r1", {
        "metrics": [
            {"subgraph": "v", "agent": "compliance",
             "metric_name": "cost_brl", "value": 0.08,
             "timestamp": "2026-01-01T00:00:00"},
        ]
    })
    assert abs(cost.total_cost_brl - 0.08) < 0.0001
    assert cost.agents[0].tokens_in == 0
    assert cost.source == "memory"
