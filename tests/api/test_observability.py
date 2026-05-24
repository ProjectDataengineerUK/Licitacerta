"""AT-001 to AT-005: SSE stream + Langfuse observability tests."""
from __future__ import annotations

import asyncio
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.store import RunStore, _SSE_CLOSE_STEPS


# ---------------------------------------------------------------------------
# Unit tests — RunStore.stream_steps()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at001_stream_steps_yields_in_order():
    store = RunStore()
    await store.create("r1", {"current_step": "start"})

    async def _advance():
        for step in ["ingested", "understood", "decided"]:
            await asyncio.sleep(0)
            await store.update("r1", {"current_step": step})

    asyncio.create_task(_advance())
    steps = [s async for s in store.stream_steps("r1")]
    assert steps == ["ingested", "understood", "decided"]


@pytest.mark.asyncio
async def test_at002_stream_unknown_run_yields_nothing():
    store = RunStore()
    steps = [s async for s in store.stream_steps("nonexistent")]
    assert steps == []


@pytest.mark.asyncio
async def test_at003_late_connect_returns_terminal_step():
    store = RunStore()
    await store.create("r2", {"current_step": "completed"})
    steps = [s async for s in store.stream_steps("r2")]
    assert steps == ["completed"]


@pytest.mark.asyncio
async def test_at003_late_connect_rejected():
    store = RunStore()
    await store.create("r3", {"current_step": "rejected"})
    steps = [s async for s in store.stream_steps("r3")]
    assert steps == ["rejected"]


@pytest.mark.asyncio
async def test_stream_steps_deduplicates_same_step():
    store = RunStore()
    await store.create("r4", {"current_step": "start"})

    async def _advance():
        await asyncio.sleep(0)  # yield so stream_steps starts waiting on queue
        await store.update("r4", {"current_step": "ingested"})
        await store.update("r4", {"current_step": "ingested"})  # duplicate — not enqueued
        await store.update("r4", {"current_step": "decided"})

    asyncio.create_task(_advance())
    steps = [s async for s in store.stream_steps("r4")]
    assert steps == ["ingested", "decided"]


@pytest.mark.asyncio
async def test_stream_steps_all_close_steps_terminate():
    for close_step in _SSE_CLOSE_STEPS:
        store = RunStore()
        await store.create("rx", {"current_step": close_step})
        steps = [s async for s in store.stream_steps("rx")]
        assert steps == [close_step]


# ---------------------------------------------------------------------------
# Unit test — get_langfuse_handler
# ---------------------------------------------------------------------------


def test_at004_no_langfuse_without_env(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    from src.observability import get_langfuse_handler

    assert get_langfuse_handler("run-1") is None


def test_at004_no_langfuse_with_only_public_key(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    from src.observability import get_langfuse_handler

    assert get_langfuse_handler("run-1") is None


def test_at004_no_langfuse_with_only_secret_key(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    from src.observability import get_langfuse_handler

    assert get_langfuse_handler("run-1") is None


# ---------------------------------------------------------------------------
# Integration tests — HTTP SSE endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at002_http_stream_404(client: AsyncClient):
    resp = await client.get("/runs/unknown-run-id/stream")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_at001_http_sse_emits_steps(client: AsyncClient):
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "Pregão 001/2026 — Obra civil", "cnpj": "12345678000195"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    steps = []
    async with client.stream("GET", f"/runs/{run_id}/stream") as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        async for line in r.aiter_lines():
            if line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                steps.append(payload["step"])

    assert len(steps) > 0
    assert steps[-1] in _SSE_CLOSE_STEPS


@pytest.mark.asyncio
async def test_at005_astream_updates_store_per_step(client: AsyncClient):
    resp = await client.post(
        "/analyze",
        json={"edital_raw": "Pregão 002/2026 — TI", "cnpj": "12345678000195"},
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    # Drain stream so pipeline finishes
    async with client.stream("GET", f"/runs/{run_id}/stream") as r:
        async for _ in r.aiter_lines():
            pass

    status = (await client.get(f"/runs/{run_id}")).json()
    assert status["current_step"] in _SSE_CLOSE_STEPS
