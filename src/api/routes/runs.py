from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.api.auth import require_role
from src.api.deps import get_graph, get_store
from src.api.models import AgentCost, ApproveRequest, RejectRequest, RunCost, RunResult, RunStatus
from src.api.store import RunStore
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
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")
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
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")
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


@router.get("/runs/{run_id}/cost", response_model=RunCost)
async def get_run_cost(
    run_id: str,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entry = await store.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")

    cost = await _try_bigquery_cost(run_id)
    if cost is not None:
        return cost

    return _cost_from_state(run_id, entry.snapshot)


async def _try_bigquery_cost(run_id: str) -> RunCost | None:
    import os
    if not os.environ.get("GCP_PROJECT_ID"):
        return None
    try:
        from src.gcp.bigquery import BigQueryWriter
        writer = BigQueryWriter.from_env()
        rows = await asyncio.to_thread(_query_agent_runs, writer, run_id)
    except Exception:
        return None
    if not rows:
        return None
    agents = [
        AgentCost(
            name=r["agent_name"],
            tokens_in=int(r.get("tokens_in") or 0),
            tokens_out=int(r.get("tokens_out") or 0),
            cost_brl=float(r.get("cost_brl") or 0.0),
            latency_ms=int(r["latency_ms"]) if r.get("latency_ms") is not None else None,
        )
        for r in rows
    ]
    return RunCost(run_id=run_id, agents=agents, total_cost_brl=sum(a.cost_brl for a in agents), source="bigquery")


def _query_agent_runs(writer, run_id: str) -> list[dict]:
    from google.cloud import bigquery as _bq
    sql = f"""
        SELECT agent_name, tokens_in, tokens_out, cost_brl, latency_ms
        FROM `{writer._project}.{writer._dataset}.agent_runs`
        WHERE run_id = @run_id
        ORDER BY created_at ASC
    """
    job_config = _bq.QueryJobConfig(
        query_parameters=[_bq.ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    return [dict(row) for row in writer._client.query(sql, job_config=job_config).result()]


def _cost_from_state(run_id: str, snapshot: dict) -> RunCost:
    metrics = snapshot.get("metrics") or []
    by_agent: dict[str, dict] = {}
    for m in metrics:
        d = m if isinstance(m, dict) else m.model_dump(mode="json")
        agent = d.get("agent", "unknown")
        slot = by_agent.setdefault(agent, {"tokens_in": 0, "tokens_out": 0, "cost_brl": 0.0, "latency_ms": None})
        if d.get("tokens_in") is not None:
            slot["tokens_in"] += int(d["tokens_in"])
        if d.get("tokens_out") is not None:
            slot["tokens_out"] += int(d["tokens_out"])
        if d.get("cost_brl") is not None:
            slot["cost_brl"] += float(d["cost_brl"])
        elif d.get("metric_name") == "cost_brl":
            slot["cost_brl"] += float(d.get("value", 0.0))
        if d.get("latency_ms") is not None:
            slot["latency_ms"] = (slot["latency_ms"] or 0) + int(d["latency_ms"])
    agents = [AgentCost(name=n, **v) for n, v in by_agent.items()]
    return RunCost(run_id=run_id, agents=agents, total_cost_brl=sum(a.cost_brl for a in agents), source="memory")


@router.get("/health")
async def health():
    return {"status": "ok"}
