from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.juridical_search import (
    JuridicalChunk,
    JuridicalSearchTool,
    _NoOpJuridicalSearchTool,
)


def _fake_embeddings(dim: int = 768):
    vec = [0.001] * dim

    class FakeEmb:
        def embed_query(self, q):
            return vec

        def embed_documents(self, ts):
            return [vec for _ in ts]

    return FakeEmb()


def _make_tool() -> JuridicalSearchTool:
    return JuridicalSearchTool(db_url="postgresql://test", embeddings=_fake_embeddings())


def _fake_conn(rows: list):
    fake_cur = MagicMock()
    fake_cur.__enter__ = lambda s: s
    fake_cur.__exit__ = MagicMock(return_value=False)
    fake_cur.fetchall.return_value = rows

    fake_conn = MagicMock()
    fake_conn.__enter__ = lambda s: s
    fake_conn.__exit__ = MagicMock(return_value=False)
    fake_conn.cursor.return_value = fake_cur
    return fake_conn, fake_cur


def test_at002_search_returns_chunks():
    rows = [("uid-1", "acordao", "2500/2015-Plenario", "TCU", "texto do acordao", 0.91)]
    fake_conn, _ = _fake_conn(rows)

    with patch("src.tools.juridical_search.psycopg.connect", return_value=fake_conn), \
         patch("src.tools.juridical_search.register_vector"):
        tool = _make_tool()
        chunks = tool.search("garantia contratual")

    assert len(chunks) == 1
    assert isinstance(chunks[0], JuridicalChunk)
    assert chunks[0].numero == "2500/2015-Plenario"
    assert chunks[0].score == pytest.approx(0.91)
    assert chunks[0].texto == "texto do acordao"


def test_at003_search_returns_empty_when_no_rows():
    fake_conn, _ = _fake_conn([])

    with patch("src.tools.juridical_search.psycopg.connect", return_value=fake_conn), \
         patch("src.tools.juridical_search.register_vector"):
        tool = _make_tool()
        result = tool.search("qualquer coisa")

    assert result == []


def test_at005_search_returns_empty_on_db_error():
    with patch("src.tools.juridical_search.psycopg.connect", side_effect=Exception("connection refused")):
        tool = _make_tool()
        result = tool.search("qualquer")

    assert result == []


def test_search_returns_empty_on_embedding_error():
    class BrokenEmb:
        def embed_query(self, q):
            raise RuntimeError("vertex down")

    tool = JuridicalSearchTool(db_url="postgresql://test", embeddings=BrokenEmb())
    result = tool.search("query")
    assert result == []


def test_noop_tool_search_always_empty():
    tool = _NoOpJuridicalSearchTool()
    assert tool.search("any") == []


@pytest.mark.asyncio
async def test_noop_tool_asearch_always_empty():
    tool = _NoOpJuridicalSearchTool()
    assert await tool.asearch("any") == []


@pytest.mark.asyncio
async def test_at006_asearch_returns_empty_on_timeout():
    class TimeoutEmb:
        def embed_query(self, q):
            raise asyncio.TimeoutError()

    tool = JuridicalSearchTool(db_url="postgresql://test", embeddings=TimeoutEmb())
    result = await tool.asearch("query")
    assert result == []


def test_from_env_returns_noop_when_no_gcp(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.setattr("src.tools.juridical_search.settings.database_url",
                        "postgresql://localhost/licitacerta")
    tool = JuridicalSearchTool.from_env()
    assert isinstance(tool, _NoOpJuridicalSearchTool)


def test_from_env_returns_noop_when_empty_db_url(monkeypatch):
    monkeypatch.setattr("src.tools.juridical_search.settings.database_url", "")
    tool = JuridicalSearchTool.from_env()
    assert isinstance(tool, _NoOpJuridicalSearchTool)


@pytest.mark.asyncio
async def test_at002_asearch_returns_chunks():
    rows = [("uid-2", "sumula", "Sumula-269", "TCU", "texto sumula", 0.85)]

    async def fake_connect(*a, **kw):
        fake_cur = AsyncMock()
        fake_cur.fetchall = AsyncMock(return_value=rows)
        fake_cur.__aenter__ = AsyncMock(return_value=fake_cur)
        fake_cur.__aexit__ = AsyncMock(return_value=False)

        fake_conn = AsyncMock()
        fake_conn.cursor = MagicMock(return_value=fake_cur)
        fake_conn.__aenter__ = AsyncMock(return_value=fake_conn)
        fake_conn.__aexit__ = AsyncMock(return_value=False)
        return fake_conn

    with patch("src.tools.juridical_search.psycopg.AsyncConnection.connect", new=fake_connect), \
         patch("src.tools.juridical_search.register_vector_async", new=AsyncMock()):
        tool = _make_tool()
        chunks = await tool.asearch("habilitação")

    assert len(chunks) == 1
    assert chunks[0].tipo == "sumula"
    assert chunks[0].score == pytest.approx(0.85)
