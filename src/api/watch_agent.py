from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import date, timedelta
from uuid import UUID

from src.api.pncp_client import PNCPClient
from src.api.store import RunStore
from src.api.watch_store import WatchStore
from src.graph.state import initial_state

_INITIAL_LOOKBACK_DAYS = int(os.getenv("WATCH_INITIAL_LOOKBACK_DAYS", "1"))

logger = logging.getLogger(__name__)


def _matches(edital: dict, keywords: list[str]) -> bool:
    texto = (edital.get("objetoCompra") or "").lower()
    return any(kw.lower() in texto for kw in keywords)


async def _trigger_analyze(
    pncp_id: str,
    objeto: str,
    cnpj: str,
    watch_config_id: UUID,
    watch_store: WatchStore,
    run_store: RunStore,
    graph,
) -> str:
    run_id = str(uuid.uuid4())
    state = initial_state(
        edital_id=pncp_id,
        edital_raw=objeto,
        company_cnpj=cnpj,
    )
    await run_store.create(run_id, dict(state))
    config = {"configurable": {"thread_id": run_id}}

    async def _run() -> None:
        from src.observability import get_langfuse_handler

        handler = get_langfuse_handler(run_id)
        run_config = {**config, "callbacks": [handler]} if handler else config
        async for chunk in graph.astream(state, run_config, stream_mode="values"):
            await run_store.update(run_id, chunk)

    task = asyncio.create_task(_run())
    await run_store.set_task(run_id, task)
    await watch_store.record(pncp_id, watch_config_id, run_id)
    return run_id


async def run_poll_cycle(
    watch_store: WatchStore,
    run_store: RunStore,
    graph,
    pncp_client: PNCPClient,
) -> None:
    configs = await watch_store.list_configs()
    today = date.today()

    for cfg in configs:
        if not cfg.active:
            continue
        since = cfg.last_polled_at.date() if cfg.last_polled_at else today - timedelta(days=_INITIAL_LOOKBACK_DAYS)
        try:
            editais = await pncp_client.search_publicacoes_all(since, today)
        except Exception:
            logger.exception("PNCP poll failed for config %s", cfg.id)
            await watch_store.update_polled_at(cfg.id)
            continue

        triggered = 0
        for edital in editais:
            pncp_id = edital.get("numeroControlePNCP", "")
            if not pncp_id:
                continue
            if not _matches(edital, cfg.keywords):
                continue
            if await watch_store.is_seen(pncp_id):
                continue

            run_id = await _trigger_analyze(
                pncp_id=pncp_id,
                objeto=edital.get("objetoCompra", pncp_id),
                cnpj=cfg.cnpj,
                watch_config_id=cfg.id,
                watch_store=watch_store,
                run_store=run_store,
                graph=graph,
            )
            triggered += 1
            logger.info("watch triggered run_id=%s for pncp_id=%s", run_id, pncp_id)

        await watch_store.update_polled_at(cfg.id)
        logger.info(
            "poll cycle config=%s editais=%d triggered=%d",
            cfg.id,
            len(editais),
            triggered,
        )


async def watch_poll_loop(
    watch_store: WatchStore,
    run_store: RunStore,
    graph,
    interval: int = 600,
) -> None:
    async with PNCPClient() as pncp_client:
        while True:
            try:
                await run_poll_cycle(watch_store, run_store, graph, pncp_client)
            except Exception:
                logger.exception("Unexpected error in watch_poll_loop")
            await asyncio.sleep(interval)
