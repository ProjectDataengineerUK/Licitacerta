from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.auth import require_role
from src.api.deps import get_graph, get_store
from src.api.models import ApproveRequest, RejectRequest, RunResult, RunStatus
from src.api.store import RunStore, _SSE_CLOSE_STEPS
from src.observability import get_langfuse_handler

router = APIRouter()

_APPROVABLE_STEPS = {"decided"}
_TERMINAL_STEPS = {"completed", "rejected", "ingestion_failed", "understanding_failed", "execution_failed"}


@router.get("/runs", response_model=list[RunStatus])
async def list_runs(
    step: str | None = Query(default=None),
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    return await store.list_all(step_filter=step)


@router.get("/runs/{run_id}", response_model=RunStatus)
async def get_run(
    run_id: str,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")
    return store.to_status(entry)


@router.get("/runs/{run_id}/results", response_model=RunResult)
async def get_results(
    run_id: str,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")
    return store.to_result(entry)


@router.post("/runs/{run_id}/approve", response_model=RunStatus)
async def approve_run(
    run_id: str,
    body: ApproveRequest,
    store: RunStore = Depends(get_store),
    graph=Depends(get_graph),
    _auth=Depends(require_role("operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")

    current_step = entry.snapshot.get("current_step")
    if current_step not in _APPROVABLE_STEPS:
        raise HTTPException(
            status_code=409,
            detail=f"run not in approvable state (current: {current_step})",
        )

    config = {"configurable": {"thread_id": run_id}}
    resume_payload = {
        "decision": "approved",
        "approver": body.approver,
        "comment": body.comment,
    }

    from langgraph.types import Command

    async def _resume() -> None:
        handler = get_langfuse_handler(run_id)
        run_config = {**config, "callbacks": [handler]} if handler else config
        async for chunk in graph.astream(
            Command(resume=resume_payload), run_config, stream_mode="values"
        ):
            await store.update(run_id, chunk)

    task = asyncio.create_task(_resume())
    await store.set_task(run_id, task)
    await store.wait(run_id)

    entry = await store.get(run_id)
    return store.to_status(entry)


@router.post("/runs/{run_id}/reject", response_model=RunStatus)
async def reject_run(
    run_id: str,
    body: RejectRequest,
    store: RunStore = Depends(get_store),
    graph=Depends(get_graph),
    _auth=Depends(require_role("operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")

    current_step = entry.snapshot.get("current_step")
    if current_step not in _APPROVABLE_STEPS:
        raise HTTPException(
            status_code=409,
            detail=f"run not in approvable state (current: {current_step})",
        )

    config = {"configurable": {"thread_id": run_id}}
    resume_payload = {
        "decision": "rejected",
        "approver": body.approver,
        "comment": body.reason,
    }

    from langgraph.types import Command

    async def _resume() -> None:
        handler = get_langfuse_handler(run_id)
        run_config = {**config, "callbacks": [handler]} if handler else config
        async for chunk in graph.astream(
            Command(resume=resume_payload), run_config, stream_mode="values"
        ):
            await store.update(run_id, chunk)

    task = asyncio.create_task(_resume())
    await store.set_task(run_id, task)
    await store.wait(run_id)

    entry = await store.get(run_id)
    return store.to_status(entry)


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_stream():
        async for step in store.stream_steps(run_id):
            yield f"data: {json.dumps({'step': step})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/health")
async def health():
    return {"status": "ok"}
