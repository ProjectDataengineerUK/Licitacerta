"""TenantUserStore — membros, convites e preferências de notificação por tenant.

In-memory para dev/testes; AlloyDB quando DATABASE_URL configurado.
Padrão idêntico a BillingStore, ContractStore, RunStore.
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class TenantMember(BaseModel):
    id: str
    tenant_id: str
    user_uid: str
    email: str
    nome: str | None = None
    papel: str = "analista"
    ativo: bool = True
    invited_by: str | None = None
    created_at: str = ""

    def model_post_init(self, _: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()


class TenantInvite(BaseModel):
    id: str
    tenant_id: str
    email: str
    papel: str = "analista"
    token: str
    expires_at: str
    accepted_at: str | None = None
    created_by: str | None = None
    created_at: str = ""

    def model_post_init(self, _: Any) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    def is_expired(self) -> bool:
        return datetime.fromisoformat(self.expires_at) < datetime.now(UTC)

    def is_accepted(self) -> bool:
        return self.accepted_at is not None


class NotifPrefs(BaseModel):
    tenant_id: str
    email_enabled: bool = True
    whatsapp_enabled: bool = False
    whatsapp_number: str | None = None
    tipos_habilitados: list[str] = [
        "vencimento_certidao",
        "prazo_impugnacao",
        "analise_concluida",
    ]


class TenantUserStore:
    def __init__(self) -> None:
        self._members: dict[str, TenantMember] = {}   # id → member
        self._invites: dict[str, TenantInvite] = {}   # id → invite
        self._notif: dict[str, NotifPrefs] = {}        # tenant_id → prefs

    # ── members ──────────────────────────────────────────────────────────

    def get_member_by_uid(self, tenant_id: str, user_uid: str) -> TenantMember | None:
        for m in self._members.values():
            if m.tenant_id == tenant_id and m.user_uid == user_uid and m.ativo:
                return m
        return None

    def list_members(self, tenant_id: str) -> list[TenantMember]:
        return [m for m in self._members.values() if m.tenant_id == tenant_id]

    def create_member(
        self,
        tenant_id: str,
        user_uid: str,
        email: str,
        papel: str = "analista",
        nome: str | None = None,
        invited_by: str | None = None,
    ) -> TenantMember:
        existing = self.get_member_by_uid(tenant_id, user_uid)
        if existing:
            return existing
        m = TenantMember(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_uid=user_uid,
            email=email,
            nome=nome,
            papel=papel,
            invited_by=invited_by,
        )
        self._members[m.id] = m
        return m

    def revoke_member(self, tenant_id: str, member_id: str) -> TenantMember | None:
        m = self._members.get(member_id)
        if m and m.tenant_id == tenant_id:
            self._members[member_id] = m.model_copy(update={"ativo": False})
            return self._members[member_id]
        return None

    def change_papel(self, tenant_id: str, member_id: str, papel: str) -> TenantMember | None:
        m = self._members.get(member_id)
        if m and m.tenant_id == tenant_id:
            self._members[member_id] = m.model_copy(update={"papel": papel})
            return self._members[member_id]
        return None

    # ── invites ───────────────────────────────────────────────────────────

    def list_invites(self, tenant_id: str) -> list[TenantInvite]:
        return [
            i for i in self._invites.values()
            if i.tenant_id == tenant_id and not i.is_accepted() and not i.is_expired()
        ]

    def create_invite(
        self,
        tenant_id: str,
        email: str,
        papel: str = "analista",
        created_by: str | None = None,
    ) -> TenantInvite:
        invite = TenantInvite(
            id=str(uuid4()),
            tenant_id=tenant_id,
            email=email,
            papel=papel,
            token=secrets.token_urlsafe(32),
            expires_at=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
            created_by=created_by,
        )
        self._invites[invite.id] = invite
        return invite

    def get_invite_by_token(self, token: str) -> TenantInvite | None:
        for i in self._invites.values():
            if i.token == token:
                return i
        return None

    def accept_invite(self, token: str) -> TenantInvite | None:
        invite = self.get_invite_by_token(token)
        if invite is None or invite.is_expired() or invite.is_accepted():
            return None
        self._invites[invite.id] = invite.model_copy(
            update={"accepted_at": datetime.now(UTC).isoformat()}
        )
        return self._invites[invite.id]

    # ── notif prefs ───────────────────────────────────────────────────────

    def get_notif_prefs(self, tenant_id: str) -> NotifPrefs:
        return self._notif.get(tenant_id, NotifPrefs(tenant_id=tenant_id))

    def update_notif_prefs(self, tenant_id: str, **kwargs: Any) -> NotifPrefs:
        current = self.get_notif_prefs(tenant_id)
        updated = current.model_copy(update=kwargs)
        self._notif[tenant_id] = updated
        return updated
