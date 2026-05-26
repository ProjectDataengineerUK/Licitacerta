from __future__ import annotations

import asyncio
from typing import Any, Callable, TypeVar

T = TypeVar("T")


async def run_in_thread(
    fn: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run a sync function in a thread pool without blocking the event loop."""
    return await asyncio.to_thread(fn, *args, **kwargs)
