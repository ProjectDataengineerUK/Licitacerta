from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.auth import require_auth
from src.services.digest_service import DigestService

router = APIRouter(prefix="/digest", tags=["digest"])


def _tenant(request: Request) -> str:
    return getattr(request.state, "tenant_id", "") or "dev-tenant"


def _pool(request: Request):
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if pool is None:
        raise HTTPException(503, "banco indisponível")
    return pool


class DigestConfigOut(BaseModel):
    tenant_id: str
    ufs: list[str] = []
    cnaes: list[str] = []
    valor_min: float | None = None
    valor_max: float | None = None
    palavras_chave: list[str] = []
    ativo: bool = True
    canal_email: bool = True
    canal_push: bool = False


class DigestConfigPut(BaseModel):
    ufs: list[str] | None = None
    cnaes: list[str] | None = None
    valor_min: float | None = Field(default=None, ge=0)
    valor_max: float | None = Field(default=None, ge=0)
    palavras_chave: list[str] | None = None
    ativo: bool | None = None
    canal_email: bool | None = None
    canal_push: bool | None = None


class DigestHistoricoItem(BaseModel):
    id: str
    digest_date: str
    itens_enviados: int
    abriu_email: bool
    clicks: int
    enviado_em: str


@router.get("/config", response_model=DigestConfigOut)
async def get_config(request: Request, _auth=Depends(require_auth)):
    async with _pool(request).acquire() as conn:
        cfg = await DigestService(conn).get_config(_tenant(request))
    return DigestConfigOut(**cfg)


@router.put("/config", response_model=DigestConfigOut)
async def put_config(body: DigestConfigPut, request: Request, _auth=Depends(require_auth)):
    if (body.valor_min is not None and body.valor_max is not None
            and body.valor_min > body.valor_max):
        raise HTTPException(400, "valor_min não pode exceder valor_max")
    async with _pool(request).acquire() as conn:
        cfg = await DigestService(conn).upsert_config(
            _tenant(request), **body.model_dump(exclude_none=True)
        )
    return DigestConfigOut(**cfg)


@router.get("/historico", response_model=list[DigestHistoricoItem])
async def get_historico(
    request: Request,
    limit: int = Query(30, ge=1, le=180),
    _auth=Depends(require_auth),
):
    async with _pool(request).acquire() as conn:
        items = await DigestService(conn).get_historico(_tenant(request), limit)
    return [DigestHistoricoItem(**i) for i in items]
