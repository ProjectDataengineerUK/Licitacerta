"""Tests for PAINEL_USUARIO — TenantUserStore, email service, config routes.

AT-001 Convite aceito — fluxo completo
AT-002 Token expirado — rejeição correta
AT-003 Visualizador bloqueado no /analyze
AT-004 Atualizar vertical da empresa
AT-005 Export JSON LGPD
AT-006 Revogar acesso de membro
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.api.tenant_user_store import TenantInvite, TenantMember, TenantUserStore


# ── TenantUserStore unit tests ───────────────────────────────────────────────


class TestTenantUserStore:
    def setup_method(self):
        self.store = TenantUserStore()
        self.tid = "tenant-abc"

    # members

    def test_create_member_returns_new(self):
        m = self.store.create_member(self.tid, "uid1", "a@b.com", "admin")
        assert m.papel == "admin"
        assert m.tenant_id == self.tid
        assert m.ativo is True

    def test_create_member_idempotent(self):
        m1 = self.store.create_member(self.tid, "uid1", "a@b.com")
        m2 = self.store.create_member(self.tid, "uid1", "a@b.com")
        assert m1.id == m2.id

    def test_get_member_by_uid(self):
        self.store.create_member(self.tid, "uid2", "b@b.com")
        m = self.store.get_member_by_uid(self.tid, "uid2")
        assert m is not None
        assert m.email == "b@b.com"

    def test_get_member_wrong_tenant_returns_none(self):
        self.store.create_member(self.tid, "uid3", "c@b.com")
        assert self.store.get_member_by_uid("other-tenant", "uid3") is None

    def test_revoke_member(self):
        m = self.store.create_member(self.tid, "uid4", "d@b.com")
        revoked = self.store.revoke_member(self.tid, m.id)
        assert revoked is not None
        assert revoked.ativo is False
        assert self.store.get_member_by_uid(self.tid, "uid4") is None  # list_active only

    def test_change_papel(self):
        m = self.store.create_member(self.tid, "uid5", "e@b.com", "analista")
        updated = self.store.change_papel(self.tid, m.id, "admin")
        assert updated is not None
        assert updated.papel == "admin"

    def test_list_members(self):
        self.store.create_member(self.tid, "u1", "a@a.com")
        self.store.create_member(self.tid, "u2", "b@a.com")
        self.store.create_member("other", "u3", "c@a.com")
        members = self.store.list_members(self.tid)
        assert len(members) == 2

    # invites

    def test_create_invite_has_token(self):
        inv = self.store.create_invite(self.tid, "x@y.com", "analista")
        assert len(inv.token) > 20
        assert inv.papel == "analista"
        assert not inv.is_accepted()

    def test_accept_invite_marks_accepted(self):
        inv = self.store.create_invite(self.tid, "x@y.com")
        result = self.store.accept_invite(inv.token)
        assert result is not None
        assert result.is_accepted()

    def test_accept_invite_twice_returns_none(self):
        inv = self.store.create_invite(self.tid, "x@y.com")
        self.store.accept_invite(inv.token)
        result = self.store.accept_invite(inv.token)
        assert result is None  # AT-002 — já aceito

    def test_accept_expired_invite_returns_none(self):
        inv = self.store.create_invite(self.tid, "exp@y.com")
        # Force expire
        expired_invite = inv.model_copy(
            update={"expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}
        )
        self.store._invites[inv.id] = expired_invite
        result = self.store.accept_invite(inv.token)
        assert result is None  # AT-002

    def test_list_invites_excludes_expired(self):
        inv = self.store.create_invite(self.tid, "old@y.com")
        self.store._invites[inv.id] = inv.model_copy(
            update={"expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}
        )
        self.store.create_invite(self.tid, "new@y.com")
        listed = self.store.list_invites(self.tid)
        assert len(listed) == 1
        assert listed[0].email == "new@y.com"

    # notif prefs

    def test_notif_prefs_defaults(self):
        prefs = self.store.get_notif_prefs(self.tid)
        assert prefs.email_enabled is True
        assert "vencimento_certidao" in prefs.tipos_habilitados

    def test_update_notif_prefs(self):
        self.store.update_notif_prefs(self.tid, email_enabled=False, whatsapp_enabled=True)
        prefs = self.store.get_notif_prefs(self.tid)
        assert prefs.email_enabled is False
        assert prefs.whatsapp_enabled is True


# ── Email service ─────────────────────────────────────────────────────────────


class TestSendInviteEmail:
    @pytest.mark.asyncio
    async def test_returns_false_without_api_key(self, monkeypatch):
        monkeypatch.delenv("RESEND_API_KEY", raising=False)
        from src.services.email import send_invite_email
        result = await send_invite_email("x@y.com", "http://localhost/invite?token=abc", "Empresa X")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_2xx(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        from src.services import email as email_mod
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(email_mod.httpx.AsyncClient, "post", mock_post):
            result = await email_mod.send_invite_email("x@y.com", "http://localhost", "Empresa X")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_4xx(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
        from src.services import email as email_mod
        mock_resp = AsyncMock()
        mock_resp.status_code = 422
        mock_resp.text = "Unprocessable"
        mock_post = AsyncMock(return_value=mock_resp)
        with patch.object(email_mod.httpx.AsyncClient, "post", mock_post):
            result = await email_mod.send_invite_email("x@y.com", "http://localhost", "Empresa X")
        assert result is False


# ── Config API (FastAPI TestClient) ──────────────────────────────────────────


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from src.api.main import create_app
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestConfigRoutes:
    def test_get_empresa_returns_200(self, client):  # AT-004 prerequisite
        r = client.get("/config/empresa")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert "cnpj" in data

    def test_patch_empresa_updates_vertical(self, client):  # AT-004
        r = client.patch("/config/empresa", json={"vertical": "tecnologia"})
        assert r.status_code == 200
        assert r.json()["vertical"] == "tecnologia"

    def test_list_usuarios_empty(self, client):
        r = client.get("/config/usuarios")
        assert r.status_code == 200
        data = r.json()
        assert "members" in data
        assert "invites" in data

    def test_convidar_and_list(self, client):  # AT-001 partial
        r = client.post("/config/usuarios/convidar", json={"email": "novo@emp.com", "papel": "analista"})
        assert r.status_code == 201
        inv = r.json()
        assert inv["email"] == "novo@emp.com"
        assert inv["papel"] == "analista"

        r2 = client.get("/config/usuarios")
        invites = r2.json()["invites"]
        assert any(i["email"] == "novo@emp.com" for i in invites)

    def test_aceitar_convite_invalid_token(self, client):  # AT-002
        r = client.post("/config/usuarios/aceitar-convite", json={"token": "token-invalido"})
        assert r.status_code == 400

    def test_convidar_role_invalido(self, client):
        r = client.post("/config/usuarios/convidar", json={"email": "x@y.com", "papel": "superadmin"})
        assert r.status_code == 400

    def test_revogar_nao_existente(self, client):  # AT-006 failure path
        r = client.delete("/config/usuarios/id-inexistente")
        assert r.status_code == 404

    def test_get_notificacoes(self, client):
        r = client.get("/config/notificacoes")
        assert r.status_code == 200
        data = r.json()
        assert "email_enabled" in data
        assert "tipos_habilitados" in data

    def test_patch_notificacoes(self, client):
        r = client.patch("/config/notificacoes", json={"email_enabled": False})
        assert r.status_code == 200
        assert r.json()["email_enabled"] is False

    def test_export_dados_200(self, client):  # AT-005
        r = client.get("/config/dados/export")
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data
        assert "contracts" in data
        assert "alerts" in data

    def test_solicitar_exclusao_202(self, client):
        r = client.request("DELETE", "/config/dados")
        assert r.status_code == 202
        assert r.json()["status"] == "solicitado"

    def test_aceitar_convite_full_flow(self, client):  # AT-001
        # create invite
        r = client.post("/config/usuarios/convidar", json={"email": "flow@test.com", "papel": "analista"})
        assert r.status_code == 201
        token = r.json()  # we need the token from the store
        # get token from store via direct lookup
        from src.api.main import app
        store = app.state.tenant_user_store
        invite = next((i for i in store._invites.values() if i.email == "flow@test.com"), None)
        assert invite is not None
        # accept
        r2 = client.post("/config/usuarios/aceitar-convite", json={"token": invite.token, "user_uid": "uid-flow"})
        assert r2.status_code == 200
        member = r2.json()
        assert member["email"] == "flow@test.com"
        assert member["papel"] == "analista"

    def test_revogar_membro(self, client):  # AT-006
        from src.api.main import app
        store = app.state.tenant_user_store
        m = store.create_member("dev-tenant", "uid-rev", "rev@test.com", "analista")
        r = client.delete(f"/config/usuarios/{m.id}")
        assert r.status_code == 204
        revoked = store._members[m.id]
        assert revoked.ativo is False
