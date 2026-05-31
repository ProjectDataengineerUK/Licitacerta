"""NOTIFICACOES_MULTICANAL — endpoints de alertas para o cockpit."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.alert_store import Alert, AlertStore
from src.api.auth import require_role
from src.api.deps import get_alert_store

router = APIRouter()


class MarkReadRequest(BaseModel):
    ids: list[str]


class MarkReadResponse(BaseModel):
    marked: int


@router.get("/alerts", response_model=list[Alert])
async def list_alerts(
    lido: bool | None = Query(default=None),
    severidade: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    store: AlertStore = Depends(get_alert_store),
    _auth=Depends(require_role("user", "operator")),
):
    return await store.list(lido=lido, severidade=severidade, page=page, page_size=page_size)


@router.post("/alerts/mark-read", response_model=MarkReadResponse)
async def mark_read(
    body: MarkReadRequest,
    store: AlertStore = Depends(get_alert_store),
    _auth=Depends(require_role("user", "operator")),
):
    n = await store.mark_read(body.ids)
    return MarkReadResponse(marked=n)
