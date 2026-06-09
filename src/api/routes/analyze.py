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
