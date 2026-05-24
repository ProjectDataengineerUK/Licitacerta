from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import Header, HTTPException


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
