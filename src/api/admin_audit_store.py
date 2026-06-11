"""AdminAuditStore — log de ações admin, append-only."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

_MAX_IN_MEMORY = 1000


class AuditEntry(BaseModel):
    id: str
    admin_email: str
    acao: str
    entidade_tipo: str | None = None
    entidade_id: str | None = None
    dados_antes: dict | None = None
    dados_depois: dict | None = None
    created_at: str = ""

    def model_post_init(self, _: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()


class AdminAuditStore:
    def __init__(self, persister: Any = None) -> None:
        self._entries: list[AuditEntry] = []
        self._persister = persister  # write-through opcional (PERSISTENCIA_STORES)

    async def hydrate(self, pool: Any) -> None:
        rows = await pool.fetch(
            "SELECT data FROM admin_audit ORDER BY created_at ASC"
        )
        self._entries = [AuditEntry.model_validate_json(r["data"]) for r in rows][-_MAX_IN_MEMORY:]

    def append(
        self,
        admin_email: str,
        acao: str,
        entidade_tipo: str | None = None,
        entidade_id: str | None = None,
        dados_antes: dict | None = None,
        dados_depois: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid4()),
            admin_email=admin_email,
            acao=acao,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
        )
        self._entries.append(entry)
        if self._persister:
            self._persister.upsert("admin_audit", {"id": entry.id}, entry.model_dump_json())
        if len(self._entries) > _MAX_IN_MEMORY:
            self._entries = self._entries[-_MAX_IN_MEMORY:]
        return entry

    def list(
        self,
        admin_email: str | None = None,
        acao: str | None = None,
        entidade_tipo: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        result = list(reversed(self._entries))
        if admin_email:
            result = [e for e in result if e.admin_email == admin_email]
        if acao:
            result = [e for e in result if e.acao == acao]
        if entidade_tipo:
            result = [e for e in result if e.entidade_tipo == entidade_tipo]
        return result[:limit]
