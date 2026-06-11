from __future__ import annotations

import logging
import os
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.services import lgpd_service

logger = logging.getLogger(__name__)

_DEFAULT_TERMS_VERSION = "2026-06-10"
_PUBLIC_PREFIXES: tuple[str, ...] = ("/lgpd/", "/health")
_PUBLIC_EXACT: frozenset[str] = frozenset(
    {"/login", "/signup", "/lgpd", "/health", "/healthz", "/docs", "/openapi.json", "/redoc"}
)


def _terms_version() -> str:
    return os.getenv("TERMS_VERSION", _DEFAULT_TERMS_VERSION)


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class ConsentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if _is_public(path):
            return await call_next(request)
        if getattr(request.state, "is_impersonating", False):
            return await call_next(request)
        user_id: str = getattr(request.state, "uid", "") or ""
        if not user_id:
            return await call_next(request)
        pool = getattr(getattr(request.app, "state", None), "_mi_pool", None)
        if pool is None:
            return await call_next(request)
        version = _terms_version()
        try:
            async with pool.acquire() as conn:
                valid = await lgpd_service.has_valid_consent(
                    user_id=user_id, version=version, conn=conn
                )
        except Exception as exc:
            logger.warning("consent_middleware: db check failed: %s", exc)
            return await call_next(request)
        if valid:
            return await call_next(request)
        return JSONResponse(
            status_code=451,
            content={
                "detail": "Consentimento LGPD pendente",
                "code": "consent_required",
                "terms_version": version,
            },
        )
