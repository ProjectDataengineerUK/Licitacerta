"""Coach Onboarding endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from src.api.auth import require_role
from src.schemas.onboarding import MarcarVistaBody, OnboardingProgress
from src.services import onboarding_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/progress", response_model=OnboardingProgress)
async def get_progress(
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if not pool:
        return OnboardingProgress(tenant_id=tenant_id)
    async with pool.acquire() as conn:
        return await onboarding_service.get_progress(tenant_id, conn)


@router.post("/marcar-vista")
async def marcar_vista(
    body: MarcarVistaBody,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if not pool:
        return {"ok": True}

    try:
        async with pool.acquire() as conn:
            await onboarding_service.marcar_vista(
                tenant_id=tenant_id,
                dica_id=body.dica_id,
                dispensar=body.dispensar,
                conn=conn,
            )
    except Exception as exc:
        logger.warning("onboarding: marcar_vista error: %s", exc)

    return {"ok": True}
