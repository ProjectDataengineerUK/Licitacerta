from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import Header, HTTPException, Request


def parse_api_keys(env_val: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for part in env_val.split(","):
        part = part.strip()
        if ":" not in part:
            continue
        key, _, role = part.partition(":")
        key = key.strip()
        role = role.strip()
        if key and role:
            keys[key] = role
    return keys


_KEY_STORE: dict[str, str] = parse_api_keys(os.getenv("LICITACERTA_API_KEYS", ""))


def require_role(*roles: str):
    async def _check(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
        if not _KEY_STORE:
            return None  # dev mode

        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing or invalid authorization header")

        provided_key = authorization.removeprefix("Bearer ").strip()

        matched_role: str | None = None
        for stored_key, role in _KEY_STORE.items():
            if hmac.compare_digest(stored_key, provided_key):
                matched_role = role
                break

        if matched_role is None:
            raise HTTPException(status_code=401, detail="invalid api key")

        if matched_role not in roles:
            raise HTTPException(status_code=403, detail=f"role '{matched_role}' not allowed")

        return {"key": provided_key, "role": matched_role}

    return _check


def require_user_role(*roles: str):
    """Verifica papel do usuário na TenantUserStore.

    Sem store populada (dev/CI) assume papel 'admin' — sem bloqueio.
    Com roles vazias, aceita qualquer usuário autenticado.
    """
    async def _check(request: Request) -> dict[str, Any] | None:
        from src.api.deps import get_tenant_user_store
        uid: str = getattr(request.state, "uid", "") or ""
        tenant_id: str = getattr(request.state, "tenant_id", "") or ""

        if not uid:
            # sem autenticação Firebase (dev mode ou bypass)
            return {"uid": "", "papel": "admin"}

        user_store = get_tenant_user_store(request)
        member = user_store.get_member_by_uid(tenant_id, uid)

        if member is None:
            # uid não cadastrado → assume admin (primeiro acesso / dev)
            return {"uid": uid, "papel": "admin"}

        if roles and member.papel not in roles:
            raise HTTPException(status_code=403, detail=f"papel '{member.papel}' não tem acesso")

        return {"uid": uid, "papel": member.papel}

    return _check


# Dependência padrão para endpoints que só exigem chamador autenticado.
require_auth = require_role("user", "operator")
