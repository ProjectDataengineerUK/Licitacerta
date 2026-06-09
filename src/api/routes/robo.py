"""Robô de lances endpoints — Business+ only."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.api.auth import require_role
from src.schemas.robo import ConfiguracaoRobo, EstrategiaLance, SessaoResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs/{run_id}/robo", tags=["robo"])

_BUSINESS_PLANS = {"business", "enterprise"}


def _require_business_plan(request: Request) -> None:
    plan = getattr(request.state, "plan", "free") or "free"
    if plan not in _BUSINESS_PLANS:
        raise HTTPException(status_code=403, detail="Funcionalidade disponível nos planos Business e Enterprise")


class AtivarRoboBody(BaseModel):
    estrategia: EstrategiaLance = EstrategiaLance.POR_POSICAO
    posicao_alvo: int = 1
    margem_minima_pct: float = 5.0
    valor_floor_brl: Decimal
    decremento_pct: float = 0.5
    intervalo_minimo_segundos: int = 20
    max_lances: int = 100


@router.post("/ativar")
async def ativar_robo(
    run_id: str,
    body: AtivarRoboBody,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)

    config = ConfiguracaoRobo(
        run_id=run_id,
        tenant_id=tenant_id,
        estrategia=body.estrategia,
        posicao_alvo=body.posicao_alvo,
        margem_minima_pct=body.margem_minima_pct,
        valor_floor_brl=body.valor_floor_brl,
        decremento_pct=body.decremento_pct,
        intervalo_minimo_segundos=body.intervalo_minimo_segundos,
        max_lances=body.max_lances,
    )

    session_id = str(uuid.uuid4())

    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO tender_sessions
                       (id, run_id, tenant_id, configuracao, status)
                       VALUES ($1,$2,$3,$4,'pendente')""",
                    uuid.UUID(session_id),
                    uuid.UUID(run_id) if len(run_id) == 36 else uuid.uuid4(),
                    uuid.UUID(tenant_id) if tenant_id else uuid.uuid4(),
                    config.model_dump_json(),
                )
        except Exception as exc:
            logger.warning("robo: failed to persist session: %s", exc)

    return {
        "session_id": session_id,
        "status": "pendente",
        "aviso": "Automação de lances está aguardando aprovação de Termos de Serviço. Nenhuma ação automática será executada.",
    }


@router.get("/status")
async def status_robo(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if not pool:
        return {"status": "sem_sessao", "lances": []}

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, status, posicao_final, valor_final_brl, motivo_encerramento
                   FROM tender_sessions WHERE run_id=$1
                   ORDER BY created_at DESC LIMIT 1""",
                uuid.UUID(run_id) if len(run_id) == 36 else uuid.uuid4(),
            )
            if not row:
                return {"status": "sem_sessao", "lances": []}
            lances = await conn.fetch(
                "SELECT numero, valor_brl, posicao_resultante, motivo, aprovado_hitl, timestamp_utc FROM session_lances WHERE session_id=$1 ORDER BY numero",
                row["id"],
            )
            return {
                "session_id": str(row["id"]),
                "status": row["status"],
                "posicao_final": row["posicao_final"],
                "valor_final_brl": float(row["valor_final_brl"]) if row["valor_final_brl"] else None,
                "motivo_encerramento": row["motivo_encerramento"],
                "lances": [dict(l) for l in lances],
            }
    except Exception as exc:
        logger.warning("robo: failed to fetch status: %s", exc)
        return {"status": "erro", "detalhe": str(exc), "lances": []}


@router.post("/parar")
async def parar_robo(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if not pool:
        return {"ok": True, "status": "encerrada"}

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE tender_sessions SET status='encerrada', encerrada_em=NOW(),
                   motivo_encerramento='parado_pelo_usuario'
                   WHERE run_id=$1 AND status NOT IN ('encerrada', 'erro')""",
                uuid.UUID(run_id) if len(run_id) == 36 else uuid.uuid4(),
            )
    except Exception as exc:
        logger.warning("robo: failed to stop session: %s", exc)

    return {"ok": True, "status": "encerrada"}
