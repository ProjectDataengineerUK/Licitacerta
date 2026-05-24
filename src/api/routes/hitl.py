"""HITL (Human-in-the-Loop) approval routes.

GET  /hitl                — list pending HITL items for tenant
POST /hitl/{run_id}/approve  — approve a HITL decision
POST /hitl/{run_id}/reject   — reject a HITL decision

Internal:
POST /internal/hitl/notify  — Cloud Tasks callback to notify approval queue
"""
from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(tags=["hitl"])


class HITLDecision(BaseModel):
    notes: str = ""


@router.get("/hitl")
async def list_hitl(request: Request) -> JSONResponse:
    tenant_id: str = getattr(request.state, "tenant_id", "dev")
    from sqlalchemy import text
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory, tenant_session
    from src.config import settings

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with tenant_session(session_factory, tenant_id) as session:
        rows = await session.execute(
            text(
                "SELECT id, run_id, action_required, payload_json, status, expires_at, created_at "
                "FROM hitl_queue WHERE status = 'pending' ORDER BY created_at ASC"
            )
        )
        items = [dict(r._mapping) for r in rows.fetchall()]

    return JSONResponse(content={"items": [_serialize(i) for i in items]})


@router.post("/hitl/{run_id}/approve", status_code=status.HTTP_200_OK)
async def approve_hitl(run_id: str, body: HITLDecision, request: Request) -> JSONResponse:
    return await _decide(run_id, "approved", body.notes, request)


@router.post("/hitl/{run_id}/reject", status_code=status.HTTP_200_OK)
async def reject_hitl(run_id: str, body: HITLDecision, request: Request) -> JSONResponse:
    return await _decide(run_id, "rejected", body.notes, request)


async def _decide(run_id: str, decision: str, notes: str, request: Request) -> JSONResponse:
    tenant_id: str = getattr(request.state, "tenant_id", "dev")
    uid: str = getattr(request.state, "uid", "unknown")
    from sqlalchemy import text
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory, tenant_session
    from src.config import settings

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with tenant_session(session_factory, tenant_id) as session:
        await session.execute(
            text(
                "UPDATE hitl_queue SET status = :status, decided_by = :uid, decided_at = NOW() "
                "WHERE run_id = :run_id AND tenant_id = :tenant_id AND status = 'pending'"
            ),
            {"status": decision, "uid": uid, "run_id": run_id, "tenant_id": tenant_id},
        )

    from src.gcp.pubsub import PubSubPublisher
    publisher = PubSubPublisher.from_env()
    publisher.publish_event(
        "hitl-decided",
        {"run_id": run_id, "tenant_id": tenant_id, "decision": decision, "notes": notes},
    )

    return JSONResponse(content={"run_id": run_id, "decision": decision})


@router.post("/internal/hitl/notify", include_in_schema=False)
async def internal_hitl_notify(request: Request) -> JSONResponse:
    payload = await request.json()
    run_id = payload.get("run_id", "")
    tenant_id = payload.get("tenant_id", "")
    from src.gcp.pubsub import PubSubPublisher
    PubSubPublisher.from_env().publish_event(
        "hitl-notification-sent",
        {"run_id": run_id, "tenant_id": tenant_id},
    )
    return JSONResponse(content={"ok": True})


def _serialize(row: dict) -> dict:
    return {k: str(v) if hasattr(v, "isoformat") else v for k, v in row.items()}
