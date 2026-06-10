from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_MENCAO_RE = re.compile(r"@(\w[\w.-]*)")

_TRANSICOES: dict[str, dict[str, set[str]]] = {
    "rascunho":   {"em_revisao": {"analista", "operator", "admin"}},
    "em_revisao": {
        "aprovado": {"operator", "admin"},
        "rascunho": {"operator", "admin"},
    },
    "aprovado": {
        "submetido":  {"operator", "admin"},
        "em_revisao": {"operator", "admin"},
    },
    "submetido": {},
}

_DEFAULT_STATUS = "rascunho"
_COMENTARIO_REMOVIDO = "[comentário removido]"


class TransicaoInvalida(ValueError):
    pass


class PermissaoNegada(PermissionError):
    pass


def extrair_mencoes(texto: str, membros_validos: set[str] | None = None) -> list[str]:
    try:
        if not texto:
            return []
        encontrados = _MENCAO_RE.findall(texto)
        vistos: list[str] = []
        for h in encontrados:
            if h not in vistos:
                vistos.append(h)
        if membros_validos is not None:
            vistos = [h for h in vistos if h in membros_validos]
        return vistos
    except Exception:
        logger.warning("extrair_mencoes falhou; retornando []", exc_info=True)
        return []


async def list_comments(pool, tenant_id: str, run_id: str) -> list[dict[str, Any]]:
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, run_id, tenant_id, user_uid, texto, mencoes,
                      deleted_at, created_at
                 FROM run_comments
                WHERE tenant_id = $1 AND run_id = $2
                ORDER BY created_at ASC""",
            tenant_id, run_id,
        )
    out: list[dict[str, Any]] = []
    for r in rows:
        deleted = r["deleted_at"] is not None
        out.append({
            "id": str(r["id"]),
            "run_id": r["run_id"],
            "user_uid": r["user_uid"],
            "texto": _COMENTARIO_REMOVIDO if deleted else r["texto"],
            "mencoes": [] if deleted else list(r["mencoes"] or []),
            "deleted": deleted,
            "created_at": r["created_at"].isoformat(),
        })
    return out


async def add_comment(
    pool, tenant_id: str, run_id: str, user_uid: str, texto: str,
    membros_validos: set[str] | None = None,
) -> dict[str, Any]:
    if pool is None:
        raise RuntimeError("DB pool indisponível")
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Comentário vazio")
    if len(texto) > 4000:
        raise ValueError("Comentário excede 4000 caracteres")

    mencoes = extrair_mencoes(texto, membros_validos)
    cid = uuid.uuid4()
    now = datetime.utcnow()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO run_comments
                   (id, run_id, tenant_id, user_uid, texto, mencoes, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7)""",
            cid, run_id, tenant_id, user_uid, texto, mencoes, now,
        )
    return {
        "id": str(cid),
        "run_id": run_id,
        "user_uid": user_uid,
        "texto": texto,
        "mencoes": mencoes,
        "deleted": False,
        "created_at": now.isoformat(),
    }


async def delete_comment(
    pool, tenant_id: str, run_id: str, comment_id: str,
    requester_uid: str, requester_role: str,
) -> None:
    if pool is None:
        raise RuntimeError("DB pool indisponível")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT user_uid, deleted_at FROM run_comments
                WHERE id = $1 AND tenant_id = $2 AND run_id = $3""",
            uuid.UUID(comment_id), tenant_id, run_id,
        )
        if row is None:
            raise KeyError("Comentário não encontrado")
        if row["deleted_at"] is not None:
            return

        is_owner = row["user_uid"] == requester_uid
        can_delete_others = requester_role in {"operator", "admin"}
        if not (is_owner or can_delete_others):
            raise PermissaoNegada("Sem permissão para remover comentário de outro usuário")

        await conn.execute(
            "UPDATE run_comments SET deleted_at = NOW() WHERE id = $1",
            uuid.UUID(comment_id),
        )


async def get_status(pool, tenant_id: str, run_id: str) -> dict[str, Any]:
    if pool is None:
        return {"run_id": run_id, "status": _DEFAULT_STATUS,
                "atualizado_por": None, "atualizado_em": None}
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT status, atualizado_por, atualizado_em
                 FROM run_approval_status
                WHERE run_id = $1 AND tenant_id = $2""",
            run_id, tenant_id,
        )
    if row is None:
        return {"run_id": run_id, "status": _DEFAULT_STATUS,
                "atualizado_por": None, "atualizado_em": None}
    return {
        "run_id": run_id,
        "status": row["status"],
        "atualizado_por": row["atualizado_por"],
        "atualizado_em": row["atualizado_em"].isoformat(),
    }


async def update_status(
    pool, tenant_id: str, run_id: str, novo_status: str,
    requester_uid: str, requester_role: str,
) -> dict[str, Any]:
    if pool is None:
        raise RuntimeError("DB pool indisponível")

    atual = (await get_status(pool, tenant_id, run_id))["status"]
    permitidas = _TRANSICOES.get(atual, {})

    if novo_status not in permitidas:
        validas = ", ".join(permitidas) or "nenhuma (estado terminal)"
        raise TransicaoInvalida(
            f"Transição '{atual}' → '{novo_status}' inválida. Permitidas: {validas}"
        )
    if requester_role not in permitidas[novo_status]:
        raise PermissaoNegada(
            f"Papel '{requester_role}' não pode mover de '{atual}' para '{novo_status}'"
        )

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO run_approval_status
                       (run_id, tenant_id, status, atualizado_por, atualizado_em)
                   VALUES ($1,$2,$3,$4,NOW())
                   ON CONFLICT (run_id) DO UPDATE
                     SET status = EXCLUDED.status,
                         atualizado_por = EXCLUDED.atualizado_por,
                         atualizado_em = NOW()""",
                run_id, tenant_id, novo_status, requester_uid,
            )
            await conn.execute(
                """INSERT INTO run_status_history
                       (run_id, tenant_id, status_anterior, status_novo, atualizado_por)
                   VALUES ($1,$2,$3,$4,$5)""",
                run_id, tenant_id, atual, novo_status, requester_uid,
            )

    return await get_status(pool, tenant_id, run_id)
