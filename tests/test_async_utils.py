from __future__ import annotations

import asyncio

import pytest

from src.graph._async_utils import run_in_thread


async def test_run_in_thread_preserves_return_value():
    def _add(a: int, b: int) -> int:
        return a + b

    result = await run_in_thread(_add, 2, 3)
    assert result == 5


async def test_run_in_thread_propagates_exception():
    def _boom() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await run_in_thread(_boom)


async def test_run_in_thread_does_not_block_event_loop():
    import time

    def _slow() -> int:
        time.sleep(0.2)
        return 42

    async def _quick() -> int:
        await asyncio.sleep(0.01)
        return 1

    t0 = time.time()
    results = await asyncio.gather(run_in_thread(_slow), _quick())
    elapsed = time.time() - t0
    assert results == [42, 1]
    assert elapsed < 0.35
