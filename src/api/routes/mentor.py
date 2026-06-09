"""Mentor conversational API — SSE streaming + history."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.auth import require_role
from src.api.deps import get_store
from src.api.store import RunStore
from src.schemas.mentor import MentorMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs/{run_id}/mentor", tags=["mentor"])


def _get_pool(request: Request) -> Any | None:
    return getattr(getattr(request.app, "state", None), "_mi_pool", None)


async def _get_or_create_conversation(run_id: str, tenant_id: str, db: Any) -> str:
    """Returns conversation_id, creating row if absent."""
    row = await db.fetchrow(
        "SELECT id FROM mentor_conversations WHERE run_id = $1", uuid.UUID(run_id)
    )
    if row:
        return str(row["id"])
    conv_id = uuid.uuid4()
    await db.execute(
        "INSERT INTO mentor_conversations (id, run_id, tenant_id) VALUES ($1, $2, $3)"
        " ON CONFLICT (run_id) DO NOTHING",
        conv_id, uuid.UUID(run_id), uuid.UUID(tenant_id) if tenant_id else conv_id,
    )
    return str(conv_id)


async def _fetch_history(conversation_id: str, db: Any) -> list[MentorMessage]:
    rows = await db.fetch(
        """SELECT role, content, tipo_resposta, acoes_sugeridas, evidencias, disclaimer
           FROM mentor_messages
           WHERE conversation_id = $1
           ORDER BY created_at ASC
           LIMIT 20""",
        uuid.UUID(conversation_id),
    )
    messages: list[MentorMessage] = []
    for r in rows:
        messages.append(MentorMessage(
            role=r["role"],
            content=r["content"],
            tipo_resposta=r["tipo_resposta"],
            acoes_sugeridas=json.loads(r["acoes_sugeridas"] or "[]"),
            evidencias=json.loads(r["evidencias"] or "[]"),
            disclaimer=r["disclaimer"],
        ))
    return messages


async def _save_message(
    conversation_id: str,
    role: str,
    content: str,
    db: Any,
    tipo_resposta: str | None = None,
    acoes_sugeridas: list | None = None,
    evidencias: list | None = None,
    disclaimer: str | None = None,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
) -> None:
    try:
        await db.execute(
            """INSERT INTO mentor_messages
               (id, conversation_id, role, content, tipo_resposta,
                acoes_sugeridas, evidencias, disclaimer, tokens_used, latency_ms)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            uuid.uuid4(),
            uuid.UUID(conversation_id),
            role,
            content,
            tipo_resposta,
            json.dumps(acoes_sugeridas or []),
            json.dumps(evidencias or []),
            disclaimer,
            tokens_used,
            latency_ms,
        )
    except Exception as exc:
        logger.warning("mentor: failed to save message: %s", exc)


class MessageBody(BaseModel):
    pergunta: str


@router.get("")
async def get_or_create(
    run_id: str,
    request: Request,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    pool = _get_pool(request)
    if not pool:
        return {"status": "sem_banco", "conversation_id": None}
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    async with pool.acquire() as conn:
        conv_id = await _get_or_create_conversation(run_id, tenant_id, conn)
    return {"conversation_id": conv_id}


@router.post("/message")
async def send_message(
    run_id: str,
    body: MessageBody,
    request: Request,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    from src.agents.mentor import MentorAgent
    from src.services.mentor_rate_limiter import check_rate_limit

    pool = _get_pool(request)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    plan = getattr(request.state, "plan", "profissional") or "profissional"

    run_state = await store.get(run_id)
    if run_state is None:
        raise HTTPException(404, "Run não encontrado")

    tender_state: dict = {}
    if run_state:
        tender = run_state.get("tender_schema")
        if tender:
            try:
                tender_state = tender.model_dump() if hasattr(tender, "model_dump") else {}
            except Exception:
                tender_state = {}

    historico: list[MentorMessage] = []
    conv_id: str | None = None

    if pool:
        async with pool.acquire() as conn:
            conv_id = await _get_or_create_conversation(run_id, tenant_id, conn)
            await check_rate_limit(plan, conv_id, conn)
            historico = await _fetch_history(conv_id, conn)
            await _save_message(conv_id, "user", body.pergunta, conn)

    agent = MentorAgent()
    t0_total = datetime.utcnow()

    async def generate():
        import time as _time
        t0 = _time.time()
        full_text = ""
        structured_json: str | None = None

        async for chunk in agent.stream(
            pergunta=body.pergunta,
            historico=historico,
            tender_state=tender_state,
            tenant_profile={},
        ):
            if chunk.startswith("[STRUCTURED]"):
                structured_json = chunk[len("[STRUCTURED]"):]
                yield f"event: structured\ndata: {structured_json}\n\n"
            else:
                full_text += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"

        if pool and conv_id and structured_json:
            try:
                from src.schemas.mentor import MentorResponse
                resp = MentorResponse.model_validate_json(structured_json)
                latency = int((_time.time() - t0) * 1000)
                async with pool.acquire() as conn:
                    await _save_message(
                        conv_id,
                        "assistant",
                        resp.resposta,
                        conn,
                        tipo_resposta=resp.tipo_resposta,
                        acoes_sugeridas=[a.model_dump() for a in resp.acoes_sugeridas],
                        evidencias=[e.model_dump() for e in resp.evidencias],
                        disclaimer=resp.disclaimer,
                        latency_ms=latency,
                    )
            except Exception as exc:
                logger.warning("mentor: error persisting assistant message: %s", exc)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history")
async def get_history(
    run_id: str,
    request: Request,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    pool = _get_pool(request)
    if not pool:
        return {"messages": [], "status": "sem_banco"}
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    async with pool.acquire() as conn:
        conv_id = await _get_or_create_conversation(run_id, tenant_id, conn)
        rows = await conn.fetch(
            """SELECT role, content, tipo_resposta, acoes_sugeridas, evidencias, disclaimer, created_at
               FROM mentor_messages
               WHERE conversation_id = $1
               ORDER BY created_at ASC
               LIMIT 50""",
            uuid.UUID(conv_id),
        )
    messages = [
        {
            "role": r["role"],
            "content": r["content"],
            "tipo_resposta": r["tipo_resposta"],
            "acoes_sugeridas": json.loads(r["acoes_sugeridas"] or "[]"),
            "evidencias": json.loads(r["evidencias"] or "[]"),
            "disclaimer": r["disclaimer"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]
    return {"conversation_id": conv_id, "messages": messages}
