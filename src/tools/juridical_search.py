from __future__ import annotations

import asyncio
import logging
from typing import Any

import psycopg
from pgvector.psycopg import register_vector, register_vector_async
from pydantic import BaseModel

from src.config import settings

logger = logging.getLogger(__name__)

_SELECT_SQL = """
    SELECT id::text, tipo, numero, fonte, texto,
           1 - (embedding <=> %s::vector) AS score
    FROM juridical_chunks
    ORDER BY embedding <=> %s::vector
    LIMIT %s
"""


class JuridicalChunk(BaseModel):
    id: str
    tipo: str
    numero: str
    fonte: str
    texto: str
    score: float


class JuridicalSearchTool:
    """Busca semântica sobre juridical_chunks via pgvector.

    Tool determinística (sem LLM): qualquer falha retorna [] em vez de propagar exceção.
    Segue o mesmo padrão de `tools/blacklist.py`.
    """

    def __init__(self, db_url: str, embeddings: Any) -> None:
        self._db_url = db_url
        self._embeddings = embeddings

    @classmethod
    def from_env(cls) -> JuridicalSearchTool:
        url = (settings.database_url or "").strip()
        if not url:
            return _NoOpJuridicalSearchTool()
        try:
            from src.gcp.vertex_ai import VertexAIEmbeddings
            embeddings = VertexAIEmbeddings.from_env()
        except Exception:
            return _NoOpJuridicalSearchTool()
        return cls(db_url=url, embeddings=embeddings)

    def search(self, query: str, top_k: int = 5) -> list[JuridicalChunk]:
        try:
            vec = self._embeddings.embed_query(query)
            with psycopg.connect(self._db_url, connect_timeout=3) as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(_SELECT_SQL, (vec, vec, top_k))
                    return self._rows_to_chunks(cur.fetchall())
        except Exception:
            logger.debug("JuridicalSearchTool.search failed — returning []", exc_info=True)
            return []

    async def asearch(self, query: str, top_k: int = 5) -> list[JuridicalChunk]:
        try:
            vec = await asyncio.to_thread(self._embeddings.embed_query, query)
            async with await psycopg.AsyncConnection.connect(self._db_url, connect_timeout=3) as conn:
                await register_vector_async(conn)
                async with conn.cursor() as cur:
                    await cur.execute(_SELECT_SQL, (vec, vec, top_k))
                    rows = await cur.fetchall()
            return self._rows_to_chunks(rows)
        except Exception:
            logger.debug("JuridicalSearchTool.asearch failed — returning []", exc_info=True)
            return []

    @staticmethod
    def _rows_to_chunks(rows: list[tuple[Any, ...]]) -> list[JuridicalChunk]:
        return [
            JuridicalChunk(id=r[0], tipo=r[1], numero=r[2], fonte=r[3], texto=r[4], score=float(r[5]))
            for r in rows
        ]


class _NoOpJuridicalSearchTool(JuridicalSearchTool):
    """Returned by from_env() when DB or GCP are not configured."""

    def __init__(self) -> None:
        self._db_url = ""
        self._embeddings = None  # type: ignore[assignment]

    def search(self, query: str, top_k: int = 5) -> list[JuridicalChunk]:
        return []

    async def asearch(self, query: str, top_k: int = 5) -> list[JuridicalChunk]:
        return []
