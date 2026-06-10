from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.auth import require_role
from src.services import colaboracao_service as svc
from src.services.colaboracao_service import PermissaoNegada, TransicaoInvalida

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/colaboracao", tags=["colaboracao"])

_BUSINESS_PLANS = {"business", "enterprise"}
_VALID_STATUS = {"rascunho", "em_revisao", "aprovado", "submetido"}


def _require_business_plan(request: Request) -> None:
    plan = getattr(request.state, "plan", "free") or "free"
    if plan not in _BUSINESS_PLANS:
        raise HTTPException(
            status_code=402,
            detail="Colaboração em equipe disponível nos planos Business e Enterprise",
        )


def _ctx(request: Request) -> tuple[Any, str, str, str]:
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    user_uid = getattr(request.state, "user_uid", "") or ""
    role = getattr(request.state, "role", "analista") or "analista"
    return pool, tenant_id, user_uid, role


def _membros_validos(request: Request, tenant_id: str) -> set[str]:
    try:
        from src.api.deps import get_tenant_user_store
        store = get_tenant_user_store(request)
        return {m.user_uid for m in store.list_members(tenant_id)}
    except Exception:
        return set()


class CommentIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)


class StatusIn(BaseModel):
    status: str


@router.get("/{run_id}/comentarios")
async def list_comentarios(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool, tenant_id, _, _ = _ctx(request)
    return await svc.list_comments(pool, tenant_id, run_id)


@router.post("/{run_id}/comentarios", status_code=201)
async def post_comentario(
    run_id: str,
    body: CommentIn,
    request: Request,
    background: BackgroundTasks,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool, tenant_id, user_uid, _ = _ctx(request)
    membros = _membros_validos(request, tenant_id)
    try:
        comment = await svc.add_comment(pool, tenant_id, run_id, user_uid, body.texto, membros)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if comment["mencoes"]:
        background.add_task(_notify_mencoes, tenant_id, run_id, comment)
    return comment


@router.delete("/{run_id}/comentarios/{comment_id}", status_code=204)
async def delete_comentario(
    run_id: str,
    comment_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool, tenant_id, user_uid, role = _ctx(request)
    try:
        await svc.delete_comment(pool, tenant_id, run_id, comment_id, user_uid, role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Comentário não encontrado") from exc
    except PermissaoNegada as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return None


@router.get("/{run_id}/status")
async def get_run_status(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    pool, tenant_id, _, _ = _ctx(request)
    return await svc.get_status(pool, tenant_id, run_id)


@router.patch("/{run_id}/status")
async def patch_run_status(
    run_id: str,
    body: StatusIn,
    request: Request,
    background: BackgroundTasks,
    _auth=Depends(require_role("user", "operator")),
):
    _require_business_plan(request)
    if body.status not in _VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"Status '{body.status}' inválido")
    pool, tenant_id, user_uid, role = _ctx(request)
    try:
        result = await svc.update_status(pool, tenant_id, run_id, body.status, user_uid, role)
    except TransicaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissaoNegada as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    background.add_task(_notify_status, tenant_id, run_id, result)
    return result


async def _notify_mencoes(tenant_id: str, run_id: str, comment: dict) -> None:
    try:
        pass  # TODO: build resolve via NotificationDispatcher
    except Exception:
        logger.warning("notify_mencoes falhou", exc_info=True)


async def _notify_status(tenant_id: str, run_id: str, status: dict) -> None:
    try:
        pass  # TODO: build resolve via NotificationDispatcher
    except Exception:
        logger.warning("notify_status falhou", exc_info=True)
