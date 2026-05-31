"""CHECKPOINT_ALLOYDB — factory de checkpointer (fallback + cleanup)."""
from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.graph.checkpoint import _is_real_db, cleanup_threads, get_checkpointer


# --------------------------------------------------------------------------- #
# _is_real_db
# --------------------------------------------------------------------------- #
def test_is_real_db_logic():
    assert _is_real_db("postgresql://user:pw@10.0.0.1:5432/licitacerta") is True
    assert _is_real_db(None) is False
    assert _is_real_db("") is False
    assert _is_real_db("postgresql://localhost/licitacerta") is False


# --------------------------------------------------------------------------- #
# AT-003 — fallback para MemorySaver
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_at003_fallback_sem_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    checkpointer, close = await get_checkpointer()
    assert isinstance(checkpointer, MemorySaver)
    await close()  # no-op idempotente


@pytest.mark.asyncio
async def test_at003_fallback_localhost(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/licitacerta")
    checkpointer, close = await get_checkpointer()
    assert isinstance(checkpointer, MemorySaver)
    await close()


# --------------------------------------------------------------------------- #
# cleanup_threads
# --------------------------------------------------------------------------- #
class _FakeSaver:
    def __init__(self):
        self.deleted: list[str] = []

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


@pytest.mark.asyncio
async def test_cleanup_threads_deleta_via_api():
    saver = _FakeSaver()
    n = await cleanup_threads(saver, ["t1", "t2", "t3"])
    assert n == 3
    assert saver.deleted == ["t1", "t2", "t3"]


@pytest.mark.asyncio
async def test_cleanup_threads_sem_suporte_ignora():
    class _NoDelete:
        pass

    n = await cleanup_threads(_NoDelete(), ["t1"])
    assert n == 0


@pytest.mark.asyncio
async def test_cleanup_threads_tolera_falha():
    class _Flaky:
        async def adelete_thread(self, tid):
            if tid == "bad":
                raise RuntimeError("boom")

    n = await cleanup_threads(_Flaky(), ["ok", "bad", "ok2"])
    assert n == 2  # 'bad' falhou mas não interrompeu


# --------------------------------------------------------------------------- #
# AT-001/002/004/005 — persistência real (requer Postgres/AlloyDB)
# --------------------------------------------------------------------------- #
@pytest.mark.integration
@pytest.mark.asyncio
async def test_at004_postgres_setup_cria_tabelas(monkeypatch):
    import os

    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL não configurado")
    monkeypatch.setenv("DATABASE_URL", db_url)
    checkpointer, close = await get_checkpointer()
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        assert isinstance(checkpointer, AsyncPostgresSaver)
    finally:
        await close()
