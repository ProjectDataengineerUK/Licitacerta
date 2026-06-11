from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.auth import require_role, require_user_role
from src.api.deps import get_graph, get_store, get_tenant_state_store
from src.api.models import AnalyzeRequest
from src.api.store import RunStore
from src.api.tenant_state_store import TenantStateStore
from src.graph.state import initial_state
from src.observability import get_langfuse_handler

router = APIRouter()


@router.get("/runs/{run_id}/pregoeiro")
async def get_run_pregoeiro(
    run_id: str,
    request: Request,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    from src.services.pregoeiro_service import PregoeicoService
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run não encontrado")
    tender = run.get("tender_schema")
    pregoeiro_nome = getattr(tender, "pregoeiro_nome", None) if tender else None
    if not pregoeiro_nome:
        return JSONResponse({"status": "nao_disponivel", "motivo": "pregoeiro_nome não identificado no edital"})
    orgao_cnpj = getattr(tender, "orgao_cnpj", "") if tender else ""
    pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
    if not pool:
        return JSONResponse({"status": "sem_dados"})
    async with pool.acquire() as conn:
        svc = PregoeicoService(conn)
        profile = await svc.lookup(nome=pregoeiro_nome, orgao_cnpj=orgao_cnpj)
    return profile.model_dump()


@router.get("/runs/{run_id}/supply-chain")
async def get_supply_chain(
    run_id: str,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run não encontrado")
    compliance = run.get("compliance")
    if compliance is None:
        raise HTTPException(404, "Análise de compliance ainda não concluída")
    sc = getattr(compliance, "supply_chain", None)
    if sc is None:
        return JSONResponse({"status": "nao_aplicavel", "motivo": "Objeto do edital não é produto"})
    return sc.model_dump()


@router.post("/analyze", status_code=202)
async def submit_edital(
    request: Request,
    body: AnalyzeRequest,
    store: RunStore = Depends(get_store),
    graph=Depends(get_graph),
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
    _auth=Depends(require_role("user", "operator")),
    _role=Depends(require_user_role("admin", "analista")),
):
    if getattr(request.state, "is_impersonating", False):
        raise HTTPException(403, "Modo de visualização — ações bloqueadas")

    tenant_id = getattr(request.state, "tenant_id", "")
    if tenant_id and tenant_state_store.is_blocked(tenant_id):
        raise HTTPException(402, "Tenant bloqueado. Entre em contato com o suporte.")

    run_id = str(uuid.uuid4())
    state = initial_state(
        edital_id=body.edital_id,
        edital_raw=body.edital_raw,
        company_cnpj=body.cnpj,
    )
    await store.create(run_id, dict(state))

    base_config = {"configurable": {"thread_id": run_id}}

    async def _run() -> None:
        handler = get_langfuse_handler(run_id)
        config = {**base_config, "callbacks": [handler]} if handler else base_config
        async for chunk in graph.astream(state, config, stream_mode="values"):
            await store.update(run_id, chunk)

    task = asyncio.create_task(_run())
    await store.set_task(run_id, task)

    return JSONResponse({"run_id": run_id}, status_code=202)
