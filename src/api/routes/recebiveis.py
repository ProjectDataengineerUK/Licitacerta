"""Recebiveis antecipacao endpoints — Business+ only."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.api.auth import require_role
from src.api.deps import get_store
from src.api.store import RunStore
from src.schemas.recebiveis import RecebiveisPendente, SimulacaoAntecipacao, SolicitacaoAntecipacao
from src.services.recebiveis_simulator import simular

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recebiveis", tags=["recebiveis"])

_BUSINESS_PLANS = {"business", "enterprise"}


def _require_business_plan(request: Request) -> None:
    plan = getattr(request.state, "plan", "free") or "free"
    if plan not in _BUSINESS_PLANS:
        raise HTTPException(status_code=403, detail="Funcionalidade disponível nos planos Business e Enterprise")


class SimularBody(BaseModel):
    valor_bruto_brl: Decimal
    prazo_dias: int
    taxa_mensal_pct: float | None = None


@router.get("/elegiveis", response_model=list[RecebiveisPendente])
async def listar_elegiveis(
    request: Request,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    return []


@router.post("/simular", response_model=SimulacaoAntecipacao)
async def simular_antecipacao(
    body: SimularBody,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    return simular(
        valor_bruto_brl=body.valor_bruto_brl,
        prazo_dias=body.prazo_dias,
        taxa_mensal_pct=body.taxa_mensal_pct,
    )


@router.post("/solicitar")
async def solicitar_antecipacao(
    body: SolicitacaoAntecipacao,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    if not body.aceite_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos para solicitar a antecipação")

    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    sim = simular(body.valor_bruto_brl, body.prazo_dias)

    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO recebiveis_solicitacoes
                       (tenant_id, run_id, valor_bruto_brl, prazo_dias,
                        taxa_mensal_pct, valor_liquido_brl, status, aceite_termos)
                       VALUES ($1,$2,$3,$4,$5,$6,'solicitado',$7)""",
                    uuid.UUID(tenant_id) if tenant_id else uuid.uuid4(),
                    uuid.UUID(body.run_id) if body.run_id else None,
                    body.valor_bruto_brl,
                    body.prazo_dias,
                    sim.taxa_mensal_pct,
                    sim.valor_liquido_brl,
                    body.aceite_termos,
                )
        except Exception as exc:
            logger.warning("recebiveis: failed to persist solicitacao: %s", exc)

    return {
        "status": "solicitado",
        "mensagem": "Sua solicitação foi registrada. Nossa equipe entrará em contato em 24h.",
        "valor_liquido_brl": float(sim.valor_liquido_brl),
    }
