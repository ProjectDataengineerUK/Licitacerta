"""AT-002: Status após ingestão. AT-006: 404 para run_id inexistente."""
import asyncio

import pytest
from httpx import AsyncClient


async def _submit(client: AsyncClient) -> str:
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "Pregão 001/2026 — Papel A4", "cnpj": "12345678000195"},
    )
    assert resp.status_code == 202
    return resp.json()["run_id"]


async def _wait_for_step(client: AsyncClient, run_id: str, target: str, timeout: float = 5.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/runs/{run_id}")
        body = resp.json()
        if body["current_step"] == target:
            return body
        await asyncio.sleep(0.05)
    return resp.json()


async def test_at002_get_run_returns_current_step(client: AsyncClient):
    run_id = await _submit(client)
    body = await _wait_for_step(client, run_id, "decided")
    assert body["run_id"] == run_id
    assert body["current_step"] == "decided"


async def test_at002_get_run_has_bid_decision(client: AsyncClient):
    run_id = await _submit(client)
    body = await _wait_for_step(client, run_id, "decided")
    assert body["bid_decision"] is not None
    assert body["bid_decision"]["recommendation"] == "participar"


async def test_at002_get_run_has_pricing(client: AsyncClient):
    run_id = await _submit(client)
    body = await _wait_for_step(client, run_id, "decided")
    assert body["pricing"] is not None


async def test_at006_unknown_run_id_returns_404(client: AsyncClient):
    resp = await client.get("/runs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "run not found"


async def test_at006_results_unknown_run_id_returns_404(client: AsyncClient):
    resp = await client.get("/runs/00000000-0000-0000-0000-000000000000/results")
    assert resp.status_code == 404


async def test_list_runs_returns_all(client: AsyncClient):
    run_id = await _submit(client)
    await _wait_for_step(client, run_id, "decided")
    resp = await client.get("/runs")
    assert resp.status_code == 200
    ids = [r["run_id"] for r in resp.json()]
    assert run_id in ids


async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
