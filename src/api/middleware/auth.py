"""Firebase ID token verification middleware.

Validates Bearer tokens issued by Firebase Auth (Google Identity Platform).
Injects `request.state.uid` and `request.state.tenant_id` for downstream handlers.
Bypasses verification when `GCP_PROJECT_ID` is not set (local dev / tests).
"""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_PUBLIC_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}
_INTERNAL_PREFIX = "/internal"


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in _PUBLIC_PATHS or path.startswith(_INTERNAL_PREFIX):
            return await call_next(request)

        if not os.environ.get("GCP_PROJECT_ID") or os.environ.get("AUTH_BYPASS") == "1":
            request.state.uid = "local-dev"
            request.state.tenant_id = request.headers.get("X-Tenant-Id", "dev")
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing Authorization header"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            uid, tenant_id = _verify_token(token)
        except Exception as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})

        request.state.uid = uid
        request.state.tenant_id = tenant_id
        return await call_next(request)


def _verify_token(token: str) -> tuple[str, str]:
    import firebase_admin  # lazy import
    from firebase_admin import auth as firebase_auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    decoded = firebase_auth.verify_id_token(token)
    uid: str = decoded["uid"]
    tenant_id: str = decoded.get("tenant_id") or decoded.get("firebase", {}).get("tenant") or uid
    return uid, tenant_id
