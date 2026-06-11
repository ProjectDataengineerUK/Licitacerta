"""AdminAuthMiddleware — protege rotas /admin/* com X-Admin-Key."""
from __future__ import annotations

import hmac
import os
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_ADMIN_PREFIX = "/admin"
_ADMIN_LOGIN_PATH = "/admin/login"


class AdminAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if not path.startswith(_ADMIN_PREFIX) or path == _ADMIN_LOGIN_PATH:
            return await call_next(request)

        if os.getenv("ADMIN_BYPASS") == "1":
            request.state.admin_email = "dev@local"
            return await call_next(request)

        key = request.headers.get("X-Admin-Key", "")
        secret = os.getenv("ADMIN_SECRET_KEY", "")
        if not secret or not hmac.compare_digest(key, secret):
            return JSONResponse(status_code=403, content={"detail": "Admin access denied"})

        request.state.admin_email = request.headers.get("X-Admin-Email", "admin@licitacerta.com.br")
        return await call_next(request)
