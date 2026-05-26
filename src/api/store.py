from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from src.api.models import RunResult, RunStatus, _serialize

logger = logging.getLogger(__name__)


def _get_cleanup_delay() -> float:
    raw = os.environ.get("QUEUE_CLEANUP_DELAY_SECONDS", "300")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 300.0

_SSE_CLOSE_STEPS = frozenset({
    "completed",
    "rejected",
    "ingestion_failed",
    "understanding_failed",
    "execution_failed",
    "decided",
})


@dataclass
class RunEntry:
    run_id: str
    snapshot: dict[str, Any]
    task: asyncio.Task | None = None
    last_step: str = ""


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunEntry] = {}
        self._queues: dict[str, asyncio.Queue] = {}
        self._cleanup_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def _cleanup_queue(self, run_id: str, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            async with self._lock:
                if run_id in self._queues:
                    del self._queues[run_id]
                    logger.debug("queue cleanup run_id=%s delay=%.1fs", run_id, delay)
                self._cleanup_tasks.pop(run_id, None)
        except asyncio.CancelledError:
            self._cleanup_tasks.pop(run_id, None)
            raise

    async def create(self, run_id: str, snapshot: dict[str, Any]) -> None:
        async with self._lock:
            self._runs[run_id] = RunEntry(run_id=run_id, snapshot=snapshot)
            self._queues[run_id] = asyncio.Queue()

    async def get(self, run_id: str) -> RunEntry | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def update(self, run_id: str, snapshot: dict[str, Any]) -> None:
        async with self._lock:
            if run_id not in self._runs:
                return
            self._runs[run_id].snapshot = snapshot
            step = snapshot.get("current_step", "")
            entry = self._runs[run_id]
            if step and step != entry.last_step and run_id in self._queues:
                entry.last_step = step
                self._queues[run_id].put_nowait(step)
                if step in _SSE_CLOSE_STEPS and run_id not in self._cleanup_tasks:
                    delay = _get_cleanup_delay()
                    task = asyncio.create_task(self._cleanup_queue(run_id, delay))
                    self._cleanup_tasks[run_id] = task

    async def set_task(self, run_id: str, task: asyncio.Task) -> None:
        async with self._lock:
            if run_id in self._runs:
                self._runs[run_id].task = task

    async def stream_steps(self, run_id: str):
        async with self._lock:
            entry = self._runs.get(run_id)
            queue = self._queues.get(run_id)

        if entry is None or queue is None:
            return

        current = entry.snapshot.get("current_step", "start")
        if current in _SSE_CLOSE_STEPS:
            yield current
            return

        while True:
            try:
                step = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                return
            yield step
            if step in _SSE_CLOSE_STEPS:
                return

    async def wait(self, run_id: str, timeout: float = 30.0) -> None:
        entry = await self.get(run_id)
        if entry and entry.task:
            await asyncio.wait_for(asyncio.shield(entry.task), timeout=timeout)

    async def list_all(self, step_filter: str | None = None) -> list[RunStatus]:
        async with self._lock:
            entries = list(self._runs.values())
        result = [self.to_status(e) for e in entries]
        if step_filter:
            result = [r for r in result if r.current_step == step_filter]
        return result

    def to_status(self, entry: RunEntry) -> RunStatus:
        s = entry.snapshot
        return RunStatus(
            run_id=entry.run_id,
            current_step=s.get("current_step", "start"),
            edital_id=s.get("edital_id", ""),
            bid_decision=_serialize(s.get("bid_decision")),
            pricing=_serialize(s.get("pricing")),
            errors=[d for e in s.get("errors", []) if (d := _serialize(e)) is not None],
        )

    def to_result(self, entry: RunEntry) -> RunResult:
        s = entry.snapshot
        return RunResult(
            run_id=entry.run_id,
            current_step=s.get("current_step", "start"),
            edital_id=s.get("edital_id", ""),
            bid_decision=_serialize(s.get("bid_decision")),
            pricing=_serialize(s.get("pricing")),
            errors=[d for e in s.get("errors", []) if (d := _serialize(e)) is not None],
            tender_schema=_serialize(s.get("tender_schema")),
            eligibility=_serialize(s.get("eligibility")),
            compliance=_serialize(s.get("compliance")),
            blacklist=_serialize(s.get("blacklist")),
            proposal_draft=_serialize(s.get("proposal_draft")),
            audit_log=[d for a in s.get("audit_log", []) if (d := _serialize(a)) is not None],
        )
