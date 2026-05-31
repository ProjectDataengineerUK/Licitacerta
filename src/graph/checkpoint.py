"""CHECKPOINT_ALLOYDB — factory de checkpointer do LangGraph.

Produção (DATABASE_URL real) usa AsyncPostgresSaver no AlloyDB para checkpointing
persistente e compartilhado entre instâncias Cloud Run. Dev/CI (sem DATABASE_URL
ou localhost) usa MemorySaver. O import do saver Postgres é lazy — o caminho de
fallback não exige o pacote `langgraph-checkpoint-postgres` instalado.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_LOCAL_DEFAULT = "postgresql://localhost/licitacerta"

# (checkpointer, close) — close é awaitable e idempotente
CheckpointerHandle = tuple[Any, Callable[[], Awaitable[None]]]


def _is_real_db(db_url: str | None) -> bool:
    """True quando há um DATABASE_URL apontando para um Postgres real (não o default local)."""
    return bool(db_url) and db_url != _LOCAL_DEFAULT


async def get_checkpointer() -> CheckpointerHandle:
    """Retorna (checkpointer, close). Use ``await close()`` no shutdown."""
    db_url = os.environ.get("DATABASE_URL")

    if not _is_real_db(db_url):
        from langgraph.checkpoint.memory import MemorySaver

        async def _noop() -> None:
            return None

        logger.info("checkpointer: MemorySaver (dev/CI — sem DATABASE_URL persistente)")
        return MemorySaver(), _noop

    # Caminho de produção — import lazy
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    assert db_url is not None  # garantido por _is_real_db acima
    cm = AsyncPostgresSaver.from_conn_string(db_url)
    saver = await cm.__aenter__()
    await saver.setup()  # cria checkpoints / checkpoint_blobs / checkpoint_writes

    async def _close() -> None:
        await cm.__aexit__(None, None, None)

    logger.info("checkpointer: AsyncPostgresSaver (AlloyDB) inicializado")
    return saver, _close


async def cleanup_threads(checkpointer: Any, thread_ids: list[str]) -> int:
    """Remove checkpoints dos threads informados (runs completados).

    Usa a API do LangGraph (``adelete_thread``); checkpointers que não a
    suportam (ex.: MemorySaver antigo) são ignorados graciosamente. A seleção de
    *quais* threads limpar (completados há > N dias) cabe ao job agendado.
    """
    adelete = getattr(checkpointer, "adelete_thread", None)
    if adelete is None:
        logger.warning("checkpointer %s não suporta adelete_thread — cleanup ignorado",
                       type(checkpointer).__name__)
        return 0
    deleted = 0
    for tid in thread_ids:
        try:
            await adelete(tid)
            deleted += 1
        except Exception as exc:  # noqa: BLE001 — cleanup best-effort
            logger.warning("falha ao limpar thread %s: %s", tid, exc)
    return deleted
