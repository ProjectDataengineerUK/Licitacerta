"""Mentor rate limiter — per-plan daily message limits."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

LIMITS: dict[str, int | None] = {
    "free":         0,     # sem acesso
    "profissional": 50,
    "business":     None,  # ilimitado
    "enterprise":   None,  # ilimitado
}


async def count_today_messages(conversation_id: str, db: Any) -> int:
    """Count user messages sent today for this conversation."""
    try:
        row = await db.fetchrow(
            """SELECT COUNT(*) AS cnt FROM mentor_messages
               WHERE conversation_id = $1
                 AND role = 'user'
                 AND created_at::date = CURRENT_DATE""",
            conversation_id,
        )
        return int(row["cnt"]) if row else 0
    except Exception as exc:
        logger.warning("mentor_rate_limiter: count error: %s", exc)
        return 0


async def check_rate_limit(plan: str, conversation_id: str, db: Any) -> None:
    limit = LIMITS.get(plan, 0)
    if limit == 0:
        raise HTTPException(status_code=403, detail="Plano não inclui o Mentor")
    if limit is None:
        return
    today_count = await count_today_messages(conversation_id, db)
    if today_count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {limit} mensagens/dia atingido",
        )
