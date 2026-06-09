"""TenantStateStore — estado de bloqueio por tenant."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


class TenantState(BaseModel):
    tenant_id: str
    blocked: bool = False
    blocked_reason: str | None = None
    blocked_at: str | None = None
    blocked_by: str | None = None
    created_at: str = ""

    def model_post_init(self, _: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()


class ImpersonationToken(BaseModel):
    token: str
    tenant_id: str
    admin_email: str
    expires_at: str

    def is_expired(self) -> bool:
        return datetime.fromisoformat(self.expires_at) < datetime.now(UTC)


class TenantStateStore:
    def __init__(self) -> None:
        self._states: dict[str, TenantState] = {}
        self._impersonation: dict[str, ImpersonationToken] = {}

    def get(self, tenant_id: str) -> TenantState | None:
        return self._states.get(tenant_id)

    def is_blocked(self, tenant_id: str) -> bool:
        s = self._states.get(tenant_id)
        return s.blocked if s else False

    def block(self, tenant_id: str, reason: str | None, by: str) -> TenantState:
        existing = self._states.get(tenant_id, TenantState(tenant_id=tenant_id))
        updated = existing.model_copy(update={
            "blocked": True,
            "blocked_reason": reason,
            "blocked_at": datetime.now(UTC).isoformat(),
            "blocked_by": by,
        })
        self._states[tenant_id] = updated
        return updated

    def unblock(self, tenant_id: str) -> TenantState:
        existing = self._states.get(tenant_id, TenantState(tenant_id=tenant_id))
        updated = existing.model_copy(update={
            "blocked": False,
            "blocked_reason": None,
            "blocked_at": None,
            "blocked_by": None,
        })
        self._states[tenant_id] = updated
        return updated

    def list_all(self) -> list[TenantState]:
        return list(self._states.values())

    # ── impersonation ─────────────────────────────────────────────────

    def create_impersonation(self, token: str, tenant_id: str, admin_email: str, expires_at: str) -> ImpersonationToken:
        imp = ImpersonationToken(token=token, tenant_id=tenant_id, admin_email=admin_email, expires_at=expires_at)
        self._impersonation[token] = imp
        return imp

    def get_impersonation(self, token: str) -> ImpersonationToken | None:
        imp = self._impersonation.get(token)
        if imp and imp.is_expired():
            del self._impersonation[token]
            return None
        return imp
