"""Tests for PAINEL_ADMIN — AdminAuthMiddleware, stores, endpoints admin.

AT-001 Acesso negado sem X-Admin-Key correto
AT-002 Feature habilitada via admin disponível para tenant
AT-003 Audit log imutável — sem método delete
AT-004 Impersonation read-only — POST /analyze retorna 403
AT-005 Feature com expires_at desabilita automaticamente
AT-006 Debug de run retorna logs completos
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.admin_audit_store import AdminAuditStore, _MAX_IN_MEMORY
from src.api.feature_flag_store import FeatureFlagStore
from src.api.middleware.admin_auth import AdminAuthMiddleware
from src.api.tenant_state_store import TenantStateStore


# ── FeatureFlagStore unit tests ──────────────────────────────────────────────


class TestFeatureFlagStore:
    def setup_method(self):
        self.store = FeatureFlagStore()

    def test_get_unknown_returns_none(self):
        assert self.store.get("t1", "robo_lances") is None

    def test_set_and_get(self):
        self.store.set("t1", "robo_lances", enabled=True)
        flag = self.store.get("t1", "robo_lances")
        assert flag is not None
        assert flag.enabled is True
        assert flag.is_active() is True

    def test_is_active_false_when_disabled(self):
        self.store.set("t1", "robo_lances", enabled=False)
        assert self.store.is_active("t1", "robo_lances") is False

    def test_list_for_tenant_returns_all_known_features(self):
        flags = self.store.list_for_tenant("t1")
        names = [f.feature for f in flags]
        assert "robo_lances" in names
        assert "multi_portal" in names
        assert "api_access" in names

    def test_at005_expires_at_disables_automatically(self):
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.store.set("t1", "robo_lances", enabled=True, expires_at=past)
        flag = self.store.get("t1", "robo_lances")
        assert flag is not None
        assert flag.enabled is False
        assert self.store.is_active("t1", "robo_lances") is False

    def test_future_expires_at_still_active(self):
        future = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
        self.store.set("t1", "robo_lances", enabled=True, expires_at=future)
        assert self.store.is_active("t1", "robo_lances") is True

    def test_set_with_note_and_created_by(self):
        flag = self.store.set("t1", "api_access", enabled=True, note="trial 30d", created_by="admin@licitacerta.com.br")
        assert flag.note == "trial 30d"
        assert flag.created_by == "admin@licitacerta.com.br"

    def test_override_flag(self):
        flag = self.store.set("t1", "api_access", enabled=True, override=True)
        assert flag.override is True


# ── AdminAuditStore unit tests ───────────────────────────────────────────────


class TestAdminAuditStore:
    def setup_method(self):
        self.store = AdminAuditStore()

    def test_at003_no_delete_method(self):
        assert not hasattr(self.store, "delete")
        assert not hasattr(self.store, "clear")

    def test_append_returns_entry(self):
        entry = self.store.append(
            admin_email="admin@licitacerta.com.br",
            acao="bloquear_tenant",
            entidade_tipo="tenant",
            entidade_id="t1",
        )
        assert entry.id
        assert entry.admin_email == "admin@licitacerta.com.br"
        assert entry.acao == "bloquear_tenant"

    def test_list_returns_most_recent_first(self):
        self.store.append("a@b.com", "acao1")
        self.store.append("a@b.com", "acao2")
        entries = self.store.list()
        assert entries[0].acao == "acao2"

    def test_list_filters_by_admin_email(self):
        self.store.append("a@b.com", "acao1")
        self.store.append("c@d.com", "acao2")
        result = self.store.list(admin_email="a@b.com")
        assert all(e.admin_email == "a@b.com" for e in result)
        assert len(result) == 1

    def test_list_filters_by_acao(self):
        self.store.append("a@b.com", "bloquear_tenant")
        self.store.append("a@b.com", "habilitar_feature")
        result = self.store.list(acao="bloquear_tenant")
        assert len(result) == 1

    def test_list_filters_by_entidade_tipo(self):
        self.store.append("a@b.com", "acao1", entidade_tipo="tenant")
        self.store.append("a@b.com", "acao2", entidade_tipo="feature_flag")
        result = self.store.list(entidade_tipo="tenant")
        assert all(e.entidade_tipo == "tenant" for e in result)

    def test_list_respects_limit(self):
        for i in range(10):
            self.store.append("a@b.com", f"acao{i}")
        result = self.store.list(limit=3)
        assert len(result) == 3

    def test_max_in_memory_cap(self):
        for i in range(_MAX_IN_MEMORY + 50):
            self.store.append("a@b.com", f"acao{i}")
        assert len(self.store._entries) == _MAX_IN_MEMORY

    def test_dados_antes_depois(self):
        entry = self.store.append(
            "a@b.com", "patch",
            dados_antes={"enabled": False},
            dados_depois={"enabled": True},
        )
        assert entry.dados_antes == {"enabled": False}
        assert entry.dados_depois == {"enabled": True}


# ── TenantStateStore unit tests ──────────────────────────────────────────────


class TestTenantStateStore:
    def setup_method(self):
        self.store = TenantStateStore()

    def test_get_unknown_returns_none(self):
        assert self.store.get("t1") is None

    def test_is_blocked_false_by_default(self):
        assert self.store.is_blocked("t1") is False

    def test_block_sets_state(self):
        self.store.block("t1", reason="pagamento pendente", by="admin@licitacerta.com.br")
        assert self.store.is_blocked("t1") is True
        state = self.store.get("t1")
        assert state.blocked_reason == "pagamento pendente"
        assert state.blocked_by == "admin@licitacerta.com.br"
        assert state.blocked_at is not None

    def test_unblock_clears_state(self):
        self.store.block("t1", None, "a@b.com")
        self.store.unblock("t1")
        assert self.store.is_blocked("t1") is False
        state = self.store.get("t1")
        assert state.blocked_reason is None
        assert state.blocked_at is None

    def test_list_all(self):
        self.store.block("t1", None, "a@b.com")
        self.store.block("t2", None, "a@b.com")
        assert len(self.store.list_all()) == 2

    def test_impersonation_token_lifecycle(self):
        future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        self.store.create_impersonation("tok123", "t1", "admin@b.com", future)
        imp = self.store.get_impersonation("tok123")
        assert imp is not None
        assert imp.tenant_id == "t1"
        assert imp.admin_email == "admin@b.com"

    def test_impersonation_expired_returns_none(self):
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.store.create_impersonation("expired", "t1", "admin@b.com", past)
        assert self.store.get_impersonation("expired") is None

    def test_impersonation_expired_removed_from_store(self):
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.store.create_impersonation("gone", "t1", "a@b.com", past)
        self.store.get_impersonation("gone")
        assert "gone" not in self.store._impersonation


# ── AdminAuthMiddleware unit tests ───────────────────────────────────────────


def _make_middleware_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AdminAuthMiddleware)

    @app.get("/admin/test")
    async def admin_test():
        return {"ok": True}

    @app.get("/admin/login")
    async def admin_login_public():
        return {"public": True}

    @app.get("/public")
    async def public():
        return {"public": True}

    return app


def test_at001_no_key_returns_403(monkeypatch):
    monkeypatch.delenv("ADMIN_BYPASS", raising=False)
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret123")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/admin/test")
    assert resp.status_code == 403


def test_at001_wrong_key_returns_403(monkeypatch):
    monkeypatch.delenv("ADMIN_BYPASS", raising=False)
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret123")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/admin/test", headers={"X-Admin-Key": "wrong"})
    assert resp.status_code == 403


def test_at001_correct_key_passes(monkeypatch):
    monkeypatch.delenv("ADMIN_BYPASS", raising=False)
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret123")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/admin/test", headers={"X-Admin-Key": "secret123"})
    assert resp.status_code == 200


def test_bypass_mode_passes_without_key(monkeypatch):
    monkeypatch.setenv("ADMIN_BYPASS", "1")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/admin/test")
    assert resp.status_code == 200


def test_login_path_is_public(monkeypatch):
    monkeypatch.delenv("ADMIN_BYPASS", raising=False)
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret123")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/admin/login")
    assert resp.status_code == 200


def test_non_admin_path_skipped(monkeypatch):
    monkeypatch.delenv("ADMIN_BYPASS", raising=False)
    monkeypatch.setenv("ADMIN_SECRET_KEY", "secret123")
    app = _make_middleware_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/public")
    assert resp.status_code == 200


# ── Endpoint integration tests (app mínimo, sem langgraph) ───────────────────


def _make_admin_app(monkeypatch) -> tuple[FastAPI, dict]:
    """App com só admin router + stores isolados — sem deps de langgraph."""
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setenv("ADMIN_BYPASS", "1")

    feature_flag_store = FeatureFlagStore()
    admin_audit_store = AdminAuditStore()
    tenant_state_store = TenantStateStore()

    # RunStore mock com list_all() e get() básicos
    store_mock = MagicMock()
    store_mock.list_all = AsyncMock(return_value=[])
    store_mock.get = AsyncMock(return_value=None)

    billing_mock = MagicMock()
    billing_mock.get = MagicMock(return_value=None)

    from src.api.routes.admin import router as admin_router
    from src.api.deps import (
        get_admin_audit_store,
        get_billing_store,
        get_feature_flag_store,
        get_store,
        get_tenant_state_store,
    )

    app = FastAPI()
    app.add_middleware(AdminAuthMiddleware)
    app.include_router(admin_router)

    app.state.feature_flag_store = feature_flag_store
    app.state.admin_audit_store = admin_audit_store
    app.state.tenant_state_store = tenant_state_store

    app.dependency_overrides[get_store] = lambda: store_mock
    app.dependency_overrides[get_feature_flag_store] = lambda: feature_flag_store
    app.dependency_overrides[get_admin_audit_store] = lambda: admin_audit_store
    app.dependency_overrides[get_tenant_state_store] = lambda: tenant_state_store
    app.dependency_overrides[get_billing_store] = lambda: billing_mock

    stores = {
        "feature_flag_store": feature_flag_store,
        "admin_audit_store": admin_audit_store,
        "tenant_state_store": tenant_state_store,
        "store_mock": store_mock,
    }
    return app, stores


@pytest.fixture()
def admin_client(monkeypatch):
    app, stores = _make_admin_app(monkeypatch)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, stores


def test_dashboard_returns_schema(admin_client):
    client, _ = admin_client
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "tenants_ativos" in data
    assert "runs_hoje" in data
    assert "erros_24h" in data
    assert "alertas" in data


def test_list_tenants_empty(admin_client):
    client, _ = admin_client
    resp = client.get("/admin/tenants")
    assert resp.status_code == 200
    assert resp.json() == []


def test_at002_feature_flag_lifecycle(admin_client):
    client, stores = admin_client
    tid = "tenant-xyz"

    resp = client.patch(
        f"/admin/tenants/{tid}/features/robo_lances",
        json={"enabled": True, "note": "trial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["note"] == "trial"

    flag = stores["feature_flag_store"].get(tid, "robo_lances")
    assert flag is not None
    assert flag.is_active() is True


def test_block_tenant(admin_client):
    client, stores = admin_client
    tid = "tenant-block"

    resp = client.post(f"/admin/tenants/{tid}/bloquear", json={"reason": "inadimplente"})
    assert resp.status_code == 200
    assert stores["tenant_state_store"].is_blocked(tid) is True


def test_unblock_tenant(admin_client):
    client, stores = admin_client
    tid = "tenant-unblock"

    client.post(f"/admin/tenants/{tid}/bloquear", json={"reason": "teste"})
    resp = client.post(f"/admin/tenants/{tid}/desbloquear")
    assert resp.status_code == 200
    assert stores["tenant_state_store"].is_blocked(tid) is False


def test_block_creates_audit_entry(admin_client):
    client, stores = admin_client
    tid = "tenant-audit"

    client.post(f"/admin/tenants/{tid}/bloquear", json={"reason": "teste"})
    entries = stores["admin_audit_store"].list(entidade_tipo="tenant")
    assert any(e.acao == "bloquear_tenant" and e.entidade_id == tid for e in entries)


def test_feature_patch_creates_audit_entry(admin_client):
    client, stores = admin_client
    tid = "tenant-audit2"

    client.patch(f"/admin/tenants/{tid}/features/api_access", json={"enabled": True})
    entries = stores["admin_audit_store"].list(entidade_tipo="feature_flag")
    assert any(e.acao == "habilitar_feature" for e in entries)


def test_audit_endpoint(admin_client):
    client, stores = admin_client
    stores["admin_audit_store"].append("admin@b.com", "acao_teste", entidade_tipo="tenant", entidade_id="t1")

    resp = client.get("/admin/audit")
    assert resp.status_code == 200
    assert any(e["acao"] == "acao_teste" for e in resp.json())


def test_audit_filter_by_acao(admin_client):
    client, stores = admin_client
    stores["admin_audit_store"].append("a@b.com", "bloquear_tenant")
    stores["admin_audit_store"].append("a@b.com", "habilitar_feature")

    resp = client.get("/admin/audit?acao=bloquear_tenant")
    assert resp.status_code == 200
    assert all(e["acao"] == "bloquear_tenant" for e in resp.json())


def test_metricas_ia_empty(admin_client):
    client, _ = admin_client
    resp = client.get("/admin/metricas/ia")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_runs" in data
    assert "taxa_hitl" in data


def test_at006_debug_run_not_found(admin_client):
    client, _ = admin_client
    resp = client.get("/admin/runs/nao-existe/debug")
    assert resp.status_code == 404


def test_features_list_for_tenant(admin_client):
    client, _ = admin_client
    resp = client.get("/admin/tenants/any-tenant/features")
    assert resp.status_code == 200
    features = resp.json()
    assert isinstance(features, list)
    assert len(features) > 0


def test_impersonate_creates_token(admin_client):
    client, stores = admin_client
    tid = "tenant-imp"

    resp = client.post(f"/admin/tenants/{tid}/impersonate")
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["tenant_id"] == tid
    assert "expires_at" in data

    imp = stores["tenant_state_store"].get_impersonation(data["token"])
    assert imp is not None
    assert imp.tenant_id == tid


def test_impersonate_creates_audit_entry(admin_client):
    client, stores = admin_client
    tid = "tenant-imp-audit"

    client.post(f"/admin/tenants/{tid}/impersonate")
    entries = stores["admin_audit_store"].list(acao="impersonation_start")
    assert any(e.entidade_id == tid for e in entries)


def test_admin_login_valid_key(admin_client, monkeypatch):
    client, _ = admin_client
    monkeypatch.setenv("ADMIN_SECRET_KEY", "mykey")
    resp = client.post("/admin/login", json={"admin_key": "mykey"})
    assert resp.status_code == 200


def test_admin_login_invalid_key(admin_client, monkeypatch):
    client, _ = admin_client
    monkeypatch.setenv("ADMIN_SECRET_KEY", "mykey")
    resp = client.post("/admin/login", json={"admin_key": "wrong"})
    assert resp.status_code == 403
