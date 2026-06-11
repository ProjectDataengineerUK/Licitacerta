from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.middleware.consent import _terms_version
from src.schemas.lgpd import ConsentBody, ConsentStatus, DeletionRequestOut
from src.services import lgpd_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["lgpd"])


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/lgpd/consent", status_code=201)
async def post_consent(body: ConsentBody, request: Request) -> dict[str, Any]:
    user_id: str = getattr(request.state, "uid", "") or ""
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Autenticação necessária"})
    if not (body.accepted_tou and body.accepted_privacy):
        return JSONResponse(
            status_code=422,
            content={"detail": "É necessário aceitar Termos de Uso e Política de Privacidade"},
        )
    version = _terms_version()
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if pool is None:
        logger.warning("lgpd.consent: sem pool — aceite não persistido (dev/CI)")
        return {"status": "ok", "version": version, "persisted": False}
    async with pool.acquire() as conn:
        await lgpd_service.log_consent(
            user_id=user_id,
            version=version,
            ip=_client_ip(request),
            accepted_tou=body.accepted_tou,
            accepted_privacy=body.accepted_privacy,
            conn=conn,
        )
    return {"status": "ok", "version": version, "persisted": True}


@router.get("/lgpd/consent/status", response_model=ConsentStatus)
async def consent_status(request: Request) -> ConsentStatus:
    version = _terms_version()
    user_id: str = getattr(request.state, "uid", "") or ""
    if not user_id:
        return ConsentStatus(version=version, has_consent=True, needs_consent=False)
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if pool is None:
        return ConsentStatus(version=version, has_consent=True, needs_consent=False)
    async with pool.acquire() as conn:
        valid = await lgpd_service.has_valid_consent(
            user_id=user_id, version=version, conn=conn
        )
    return ConsentStatus(version=version, has_consent=valid, needs_consent=not valid)


@router.delete("/account/lgpd/revogar", status_code=202, response_model=DeletionRequestOut)
async def revogar(request: Request) -> Any:
    user_id: str = getattr(request.state, "uid", "") or ""
    tenant_id: str = getattr(request.state, "tenant_id", "") or ""
    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Autenticação necessária"})
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if pool is None:
        return DeletionRequestOut(
            id="",
            tenant_id=tenant_id,
            status="pending",
            mensagem="Solicitação recebida (dev: não persistida). Art. 18 LGPD.",
        )
    async with pool.acquire() as conn:
        result = await lgpd_service.request_deletion(
            tenant_id=tenant_id, user_id=user_id, conn=conn
        )
    return DeletionRequestOut(
        id=result["id"],
        tenant_id=result["tenant_id"],
        status=result["status"],
        scheduled_delete_at=result["scheduled_delete_at"],
        mensagem="Solicitação recebida. Dados serão eliminados em até 30 dias (LGPD Art. 18).",
    )
