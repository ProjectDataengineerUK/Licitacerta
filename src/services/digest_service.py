from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "ufs": [], "cnaes": [], "valor_min": None, "valor_max": None,
    "palavras_chave": [], "ativo": True, "canal_email": True, "canal_push": False,
}


class DigestService:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def get_config(self, tenant_id: str) -> dict:
        row = await self._conn.fetchrow(
            "SELECT * FROM digest_config WHERE tenant_id = $1", tenant_id
        )
        if not row:
            return {"tenant_id": tenant_id, **_DEFAULT_CONFIG}
        return {
            "tenant_id": row["tenant_id"],
            "ufs": list(row["ufs"] or []),
            "cnaes": list(row["cnaes"] or []),
            "valor_min": float(row["valor_min"]) if row["valor_min"] is not None else None,
            "valor_max": float(row["valor_max"]) if row["valor_max"] is not None else None,
            "palavras_chave": list(row["palavras_chave"] or []),
            "ativo": row["ativo"],
            "canal_email": row["canal_email"],
            "canal_push": row["canal_push"],
        }

    async def upsert_config(self, tenant_id: str, **fields: Any) -> dict:
        cfg = {**_DEFAULT_CONFIG, **{k: v for k, v in fields.items() if v is not None}}
        await self._conn.execute(
            """INSERT INTO digest_config (
                   tenant_id, ufs, cnaes, valor_min, valor_max,
                   palavras_chave, ativo, canal_email, canal_push, updated_at
               ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9, NOW())
               ON CONFLICT (tenant_id) DO UPDATE SET
                   ufs            = EXCLUDED.ufs,
                   cnaes          = EXCLUDED.cnaes,
                   valor_min      = EXCLUDED.valor_min,
                   valor_max      = EXCLUDED.valor_max,
                   palavras_chave = EXCLUDED.palavras_chave,
                   ativo          = EXCLUDED.ativo,
                   canal_email    = EXCLUDED.canal_email,
                   canal_push     = EXCLUDED.canal_push,
                   updated_at     = NOW()""",
            tenant_id, cfg["ufs"], cfg["cnaes"], cfg["valor_min"], cfg["valor_max"],
            cfg["palavras_chave"], cfg["ativo"], cfg["canal_email"], cfg["canal_push"],
        )
        return await self.get_config(tenant_id)

    async def log_digest(self, tenant_id: str, digest_date: date, itens: int) -> bool:
        result = await self._conn.execute(
            """INSERT INTO digest_log (tenant_id, digest_date, itens_enviados)
               VALUES ($1, $2, $3)
               ON CONFLICT (tenant_id, digest_date) DO NOTHING""",
            tenant_id, digest_date, itens,
        )
        return result.endswith("1")

    async def get_historico(self, tenant_id: str, limit: int = 30) -> list[dict]:
        rows = await self._conn.fetch(
            """SELECT id, digest_date, itens_enviados, abriu_email, clicks, enviado_em
               FROM digest_log WHERE tenant_id = $1
               ORDER BY digest_date DESC LIMIT $2""",
            tenant_id, limit,
        )
        return [
            {
                "id": str(r["id"]),
                "digest_date": r["digest_date"].isoformat(),
                "itens_enviados": r["itens_enviados"],
                "abriu_email": r["abriu_email"],
                "clicks": r["clicks"],
                "enviado_em": r["enviado_em"].isoformat(),
            }
            for r in rows
        ]
