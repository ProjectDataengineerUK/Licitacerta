"""Certidões routes — asyncpg + plan gate. Replaces legacy SQLAlchemy version."""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.services import certidao_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/certidoes", tags=["certidoes"])

_PROFISSIONAL_PLANS = {"profissional", "business", "enterprise"}


def _plan(request: Request) -> str:
    return getattr(request.state, "plan", "free") or "free"


def _pool(request: Request):
    return getattr(getattr(request.app, "state", None), "_mi_pool", None)


def _serialize(row: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}


class CertidaoIn(BaseModel):
    cnpj: str
    tipo: str
    validade: date | None = None
    url_documento: str | None = None


class CertidaoUpdate(BaseModel):
    validade: date | None = None
    url_documento: str | None = None


@router.get("")
async def list_certidoes(request: Request) -> dict:
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = _pool(request)
    if not pool:
        return {"certidoes": [], "alertas_habilitados": _plan(request) in _PROFISSIONAL_PLANS}
    try:
        async with pool.acquire() as conn:
            rows = await svc.listar(conn, tenant_id)
    except Exception as exc:
        logger.warning("certidoes: list falhou: %s", exc)
        rows = []
    return {
        "certidoes": [_serialize(r) for r in rows],
        "alertas_habilitados": _plan(request) in _PROFISSIONAL_PLANS,
    }


@router.post("", status_code=201)
async def create_certidao(body: CertidaoIn, request: Request) -> dict:
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    if body.tipo not in svc.TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo inválido: {body.tipo}")
    pool = _pool(request)
    if not pool:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        async with pool.acquire() as conn:
            row = await svc.criar(
                conn, tenant_id, body.cnpj, body.tipo, body.validade, body.url_documento
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("certidoes: create falhou: %s", exc)
        raise HTTPException(status_code=503, detail="Falha ao salvar certidão") from exc
    return _serialize(row)


@router.put("/{certidao_id}")
async def update_certidao(certidao_id: str, body: CertidaoUpdate, request: Request) -> dict:
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = _pool(request)
    if not pool:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        async with pool.acquire() as conn:
            row = await svc.atualizar(
                conn, tenant_id, certidao_id, body.validade, body.url_documento
            )
    except Exception as exc:
        logger.warning("certidoes: update falhou: %s", exc)
        raise HTTPException(status_code=503, detail="Falha ao atualizar") from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Certidão não encontrada")
    return _serialize(row)


@router.get("/{certidao_id}/alertas")
async def get_alertas(certidao_id: str, request: Request) -> dict:
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    habilitado = _plan(request) in _PROFISSIONAL_PLANS
    pool = _pool(request)
    if not pool:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT validade, ultimo_alerta FROM certidoes WHERE tenant_id=$1 AND id=$2",
            tenant_id,
            certidao_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Certidão não encontrada")
    decisao = svc.check_alertas(row["validade"], row["ultimo_alerta"])
    return {
        "alertas_habilitados": habilitado,
        "deve_alertar": decisao.deve_alertar and habilitado,
        "dias_restantes": decisao.dias_restantes,
        "marco": decisao.marco,
        "severidade": decisao.severidade,
        "upsell": (not habilitado),
    }
