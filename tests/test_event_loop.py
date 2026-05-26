from __future__ import annotations

import asyncio
import time

import pytest

from src.graph._async_utils import run_in_thread


def _slow_fn(duration: float) -> str:
    time.sleep(duration)
    return "done"


@pytest.mark.asyncio
async def test_at001_run_in_thread_does_not_block_event_loop():
    """Concurrent tasks: slow fn in thread + fast coroutine both complete quickly."""
    results = {}

    async def fast_task():
        await asyncio.sleep(0.01)
        results["fast"] = time.monotonic()

    async def slow_task():
        await run_in_thread(_slow_fn, 0.3)
        results["slow"] = time.monotonic()

    t0 = time.monotonic()
    await asyncio.gather(slow_task(), fast_task())
    elapsed = time.monotonic() - t0

    assert "fast" in results
    assert "slow" in results
    assert elapsed < 0.5
    assert results["fast"] < results["slow"]


@pytest.mark.asyncio
async def test_at001_event_loop_responsive_during_concurrent_runs():
    """Health-check latency stays low while 3 slow tasks run concurrently."""

    async def slow_task():
        await run_in_thread(_slow_fn, 0.3)

    async def health_check() -> float:
        t0 = time.monotonic()
        await asyncio.sleep(0)
        return time.monotonic() - t0

    slow_tasks = [asyncio.create_task(slow_task()) for _ in range(3)]
    await asyncio.sleep(0.05)

    latency = await health_check()
    assert latency < 0.1, f"Event loop blocked: health check took {latency:.3f}s"

    await asyncio.gather(*slow_tasks)
