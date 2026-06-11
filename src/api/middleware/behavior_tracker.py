"""Behavior tracker middleware — auto-marks onboarding dicas based on page visits."""
from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Map path prefixes → dica_id to auto-mark as visited
_PATH_DICA_MAP: dict[str, str] = {
    "/runs/new":     "d01_upload",
    "/runs/":        "d02_resultado",
    "/portfolio":    "d04_portfolio",
    "/recebiveis":   "d05_recebiveis",
    "/mentor":       "d06_mentor",
}


class BehaviorTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)

        # Only track GET requests with a logged-in tenant
        if request.method != "GET":
            return response

        tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
        if not tenant_id:
            return response

        path = request.url.path
        dica_id: str | None = None
        for prefix, did in _PATH_DICA_MAP.items():
            if path.startswith(prefix):
                dica_id = did
                break

        if not dica_id:
            return response

        pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
        if not pool:
            return response

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO onboarding_progresso (tenant_id, dica_id, visto_em)
                       VALUES ($1,$2,NOW())
                       ON CONFLICT (tenant_id, dica_id) DO NOTHING""",
                    tenant_id, dica_id,
                )
        except Exception as exc:
            logger.debug("behavior_tracker: failed to mark dica: %s", exc)

        return response
