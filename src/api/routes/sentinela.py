"""Sentinela MLOps endpoints — evals, drift, prompt rollback, cost, source health."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.api.auth import require_role
from src.sentinela.data_quality_checker import check_all_sources
from src.sentinela.drift_detector import DriftDetector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentinela", tags=["sentinela"])


@router.get("/sources")
async def get_source_health(_auth=Depends(require_role("operator", "admin"))):
    results = await check_all_sources()
    return [
        {
            "source_name": r.source_name,
            "is_fresh": r.is_fresh,
            "latency_ms": r.latency_ms,
            "editais_count": r.editais_count,
            "error": r.error,
            "checked_at": r.checked_at,
        }
        for r in results
    ]


@router.get("/drift")
async def get_drift_report(_auth=Depends(require_role("operator", "admin"))):
    detector = DriftDetector()
    agents = ["compliance", "bid_no_bid", "impugnacao"]
    reports = [detector.detect_output_drift(a) for a in agents]
    return [
        {
            "agent_name": r.agent_name,
            "drift_detected": r.drift_detected,
            "kl_divergence": r.kl_divergence,
            "current_sample_n": r.current_sample_n,
            "baseline_sample_n": r.baseline_sample_n,
            "data_insuficiente": r.data_insuficiente,
            "message": r.message,
        }
        for r in reports
    ]


@router.post("/prompts/{agent_name}/rollback")
async def rollback_prompt(
    agent_name: str,
    body: dict,
    _auth=Depends(require_role("admin")),
):
    target_version = body.get("version")
    if not target_version:
        raise HTTPException(400, "Campo 'version' obrigatório")
    try:
        from src.prompts.registry import rollback_prompt as _rollback
        await _rollback(agent_name, target_version)
        return {"status": "ok", "agent": agent_name, "active_version": target_version}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        logger.error("prompt rollback failed: %s", exc)
        raise HTTPException(500, f"Rollback falhou: {exc}") from exc


@router.get("/prompts/{agent_name}")
async def list_prompt_versions(
    agent_name: str,
    _auth=Depends(require_role("operator", "admin")),
):
    try:
        import asyncpg
        import os
        url = os.environ.get("DATABASE_URL")
        if not url:
            return JSONResponse({"versions": [], "error": "DATABASE_URL not set"})
        conn = await asyncpg.connect(url)
        try:
            rows = await conn.fetch(
                "SELECT version, hash, author, eval_score, active, deployed_at, rolled_back, created_at "
                "FROM prompt_versions WHERE agent_name = $1 ORDER BY created_at DESC LIMIT 20",
                agent_name,
            )
        finally:
            await conn.close()
        return {
            "agent_name": agent_name,
            "versions": [dict(r) for r in rows],
        }
    except Exception as exc:
        logger.error("list_prompt_versions: %s", exc)
        raise HTTPException(500, str(exc)) from exc


@router.get("/runs/{run_id}/trace")
async def get_run_trace(
    run_id: str,
    _auth=Depends(require_role("user", "operator", "admin")),
):
    from src.api.deps import get_store
    from fastapi import Request
    # Lightweight: return audit_log + metrics from run store
    try:
        import asyncpg
        import os
        url = os.environ.get("DATABASE_URL")
        if not url:
            return JSONResponse({"error": "DATABASE_URL not set"})
        conn = await asyncpg.connect(url)
        try:
            row = await conn.fetchrow(
                "SELECT state FROM runs WHERE id = $1 LIMIT 1",
                run_id,
            )
        finally:
            await conn.close()
        if not row:
            raise HTTPException(404, "Run não encontrado")
        import json
        state = json.loads(row["state"]) if isinstance(row["state"], str) else dict(row["state"])
        return {
            "run_id": run_id,
            "audit_log": state.get("audit_log", []),
            "metrics": state.get("metrics", []),
            "errors": state.get("errors", []),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_run_trace: %s", exc)
        raise HTTPException(500, str(exc)) from exc
