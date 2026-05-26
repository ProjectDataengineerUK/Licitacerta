from __future__ import annotations

import asyncio
import os

import pytest

from src.api.store import RunStore, _get_cleanup_delay


@pytest.fixture()
async def store():
    return RunStore()


async def _make_run(store: RunStore, run_id: str = "r1") -> None:
    await store.create(run_id, {"current_step": "start"})


@pytest.mark.asyncio
async def test_at002_queue_removed_after_terminal_step(monkeypatch):
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "0.05")
    store = RunStore()
    await _make_run(store)
    await store.update("r1", {"current_step": "completed"})
    assert "r1" in store._queues
    await asyncio.sleep(0.2)
    assert "r1" not in store._queues


@pytest.mark.asyncio
async def test_at002_run_entry_preserved_for_audit(monkeypatch):
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "0.05")
    store = RunStore()
    await _make_run(store)
    await store.update("r1", {"current_step": "completed"})
    await asyncio.sleep(0.2)
    assert await store.get("r1") is not None


@pytest.mark.asyncio
async def test_at003_cleanup_does_not_touch_active_runs(monkeypatch):
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "0.05")
    store = RunStore()
    await _make_run(store, "active")
    await _make_run(store, "terminal")
    await store.update("terminal", {"current_step": "rejected"})
    await asyncio.sleep(0.2)
    assert "active" in store._queues
    assert "terminal" not in store._queues


@pytest.mark.asyncio
async def test_cleanup_delay_invalid_env_falls_back_to_300(monkeypatch):
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "not-a-number")
    assert _get_cleanup_delay() == 300.0


@pytest.mark.asyncio
async def test_cleanup_task_is_idempotent_for_same_run(monkeypatch):
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "60")
    store = RunStore()
    await _make_run(store)
    await store.update("r1", {"current_step": "completed"})
    await store.update("r1", {"current_step": "completed"})
    assert len(store._cleanup_tasks) == 1
    store._cleanup_tasks["r1"].cancel()
