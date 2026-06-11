"""PERSISTENCIA_STORES — Persister: write-through assíncrono para stores sync.

Stores de interface síncrona (TenantUserStore etc.) não podem fazer I/O direto.
Mutações enfileiram upserts aqui; uma task de flush grava em lote no AlloyDB.
Falha de persistência NUNCA quebra a request (log ERROR + retry).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_FLUSH_INTERVAL_S = 2.0
_FLUSH_BATCH = 50
_MAX_RETRIES = 3


class Persister:
    """Fila de upserts (table, pk_cols, data_json) com flush em background."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self._queue: asyncio.Queue[tuple[str, dict[str, Any], str]] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._closed = False

    def upsert(self, table: str, pk: dict[str, Any], data_json: str) -> None:
        """Fire-and-forget. Seguro chamar de código sync dentro do event loop."""
        if self._closed:
            return
        self._queue.put_nowait((table, pk, data_json))
        self._ensure_task()

    def _ensure_task(self) -> None:
        if self._task is None or self._task.done():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("persister: sem event loop ativo — upsert ficará na fila")
                return
            self._task = loop.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        while not (self._closed and self._queue.empty()):
            batch: list[tuple[str, dict[str, Any], str]] = []
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=_FLUSH_INTERVAL_S)
                batch.append(item)
            except TimeoutError:
                if self._closed:
                    break
                continue
            while len(batch) < _FLUSH_BATCH and not self._queue.empty():
                batch.append(self._queue.get_nowait())
            await self._write_batch(batch)

    async def _write_batch(self, batch: list[tuple[str, dict[str, Any], str]]) -> None:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with self._pool.acquire() as conn:
                    for table, pk, data_json in batch:
                        cols = list(pk.keys()) + ["data"]
                        vals = list(pk.values()) + [data_json]
                        placeholders = ", ".join(f"${i + 1}" for i in range(len(vals)))
                        pk_cols = ", ".join(pk.keys())
                        await conn.execute(
                            f"INSERT INTO {table} ({', '.join(cols)}) "
                            f"VALUES ({placeholders}) "
                            f"ON CONFLICT ({pk_cols}) DO UPDATE SET data = EXCLUDED.data",
                            *vals[:-1],
                            vals[-1],
                        )
                return
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error("persister: batch perdido após %d tentativas: %s", attempt, exc)
                    return
                await asyncio.sleep(0.5 * 2**attempt)

    async def aclose(self) -> None:
        """Drena a fila no shutdown do lifespan."""
        self._closed = True
        if self._task is not None and not self._task.done():
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                logger.error("persister: shutdown com %d itens não gravados", self._queue.qsize())
