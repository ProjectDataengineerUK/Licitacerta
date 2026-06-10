from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from src.api.auth import require_role

router = APIRouter(prefix="/ativacao", tags=["ativacao"])


def _pool(request: Request):
    return getattr(getattr(request.app, "state", None), "_mi_pool", None)


class StepIn(BaseModel):
    step: int
    flags: dict = {}


class CnpjIn(BaseModel):
    cnpj: str


@router.get("/status")
async def status(request: Request, _auth=Depends(require_role("user", "operator", "admin"))):
    from src.services.ativacao_service import get_status

    tenant_id = getattr(request.state, "tenant_id", None)
    pool = _pool(request)
    if not pool:
        return {"tenant_id": tenant_id, "step_atual": 0, "ativado": False}
    return await get_status(tenant_id, pool)


@router.post("/cnpj-lookup")
async def cnpj_lookup(
    body: CnpjIn,
    request: Request,
    _auth=Depends(require_role("user", "operator", "admin")),
):
    from src.services.ativacao_service import cnpj_lookup as _lookup

    return await _lookup(body.cnpj)


@router.post("/step")
async def update_step(
    body: StepIn,
    request: Request,
    _auth=Depends(require_role("user", "operator", "admin")),
):
    from src.services.ativacao_service import update_step as _update

    tenant_id = getattr(request.state, "tenant_id", None)
    pool = _pool(request)
    if not pool:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    await _update(tenant_id, body.step, body.flags, pool)
    return {"ok": True}


@router.post("/concluir")
async def concluir(
    request: Request,
    _auth=Depends(require_role("user", "operator", "admin")),
):
    from src.services.ativacao_service import concluir as _concluir

    tenant_id = getattr(request.state, "tenant_id", None)
    pool = _pool(request)
    if not pool:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    notifications = getattr(getattr(request.app, "state", None), "notifications", None)
    await _concluir(tenant_id, pool, notifications)
    return {"ativado": True}
