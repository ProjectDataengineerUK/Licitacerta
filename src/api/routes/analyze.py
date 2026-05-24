from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.auth import require_role
from src.api.deps import get_graph, get_store
from src.api.models import AnalyzeRequest
from src.api.store import RunStore
from src.graph.state import initial_state
from src.observability import get_langfuse_handler

router = APIRouter()


@router.post("/analyze", status_code=202)
async def submit_edital(
    body: AnalyzeRequest,
    store: RunStore = Depends(get_store),
    graph=Depends(get_graph),
    _auth=Depends(require_role("user", "operator")),
):
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
