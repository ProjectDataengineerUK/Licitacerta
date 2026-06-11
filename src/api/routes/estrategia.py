"""Estrategia Competitiva endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.api.auth import require_role
from src.api.deps import get_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/runs/{run_id}/estrategia")
async def get_estrategia(
    run_id: str,
    store=Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run não encontrado")
    result = run.get("estrategia_result")
    if result is None:
        return JSONResponse({"status": "nao_disponivel"}, status_code=404)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


@router.patch("/runs/{run_id}/estrategia/acoes/{numero}")
async def toggle_acao(
    run_id: str,
    numero: int,
    body: dict,
    store=Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    concluida: bool = body.get("concluida", True)

    try:
        import os

        import asyncpg
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise HTTPException(503, "DATABASE_URL not set")
        conn = await asyncpg.connect(url)
        try:
            rows = await conn.execute(
                """UPDATE estrategia_acoes
                   SET concluida = $1, concluida_em = CASE WHEN $1 THEN NOW() ELSE NULL END
                   WHERE run_id = $2 AND numero = $3""",
                concluida,
                run_id,
                numero,
            )
        finally:
            await conn.close()
        if rows == "UPDATE 0":
            raise HTTPException(404, f"Ação {numero} não encontrada para run {run_id}")
        return {"run_id": run_id, "numero": numero, "concluida": concluida}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("toggle_acao: %s", exc)
        raise HTTPException(500, str(exc)) from exc
