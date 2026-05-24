from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.auth import require_role
from src.api.deps import get_pncp_client, get_watch_store
from src.api.pncp_client import PNCPClient
from src.api.watch_store import WatchConfig, WatchStore

router = APIRouter(prefix="/watch")


class CreateWatchConfigRequest(BaseModel):
    keywords: list[str]
    cnpj: str


class WatchConfigResponse(BaseModel):
    id: UUID
    keywords: list[str]
    cnpj: str
    active: bool
    last_polled_at: str | None = None


def _to_response(cfg: WatchConfig) -> WatchConfigResponse:
    return WatchConfigResponse(
        id=cfg.id,
        keywords=cfg.keywords,
        cnpj=cfg.cnpj,
        active=cfg.active,
        last_polled_at=cfg.last_polled_at.isoformat() if cfg.last_polled_at else None,
    )


@router.post("/configs", status_code=201)
async def create_config(
    body: CreateWatchConfigRequest,
    watch_store: WatchStore = Depends(get_watch_store),
    _auth=Depends(require_role("operator")),
):
    cfg = await watch_store.create_config(keywords=body.keywords, cnpj=body.cnpj)
    return _to_response(cfg)


@router.get("/configs", response_model=list[WatchConfigResponse])
async def list_configs(
    watch_store: WatchStore = Depends(get_watch_store),
    _auth=Depends(require_role("user", "operator")),
):
    configs = await watch_store.list_configs()
    return [_to_response(c) for c in configs]


@router.delete("/configs/{config_id}", status_code=204)
async def delete_config(
    config_id: UUID,
    watch_store: WatchStore = Depends(get_watch_store),
    _auth=Depends(require_role("operator")),
):
    deleted = await watch_store.delete_config(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="watch config not found")


@router.post("/poll", status_code=202)
async def manual_poll(
    request: Request,
    watch_store: WatchStore = Depends(get_watch_store),
    pncp_client: PNCPClient = Depends(get_pncp_client),
    _auth=Depends(require_role("operator")),
):
    from src.api.watch_agent import run_poll_cycle

    await run_poll_cycle(
        watch_store,
        request.app.state.store,
        request.app.state.graph,
        pncp_client,
    )
    return JSONResponse({"status": "poll triggered"}, status_code=202)
