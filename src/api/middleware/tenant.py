"""Tenant context middleware.

Reads `request.state.tenant_id` (set by FirebaseAuthMiddleware) and
makes it available via a request-scoped context var for AlloyDB sessions.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

current_tenant_id: ContextVar[str] = ContextVar("current_tenant_id", default="")


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = getattr(request.state, "tenant_id", "")
        token = current_tenant_id.set(tenant_id)
        try:
            return await call_next(request)
        finally:
            current_tenant_id.reset(token)
