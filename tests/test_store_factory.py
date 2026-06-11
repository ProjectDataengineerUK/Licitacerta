"""PERSISTENCIA_STORES — factory, persister e write-through (unit, sem banco)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.admin_audit_store import AdminAuditStore
from src.api.alert_store import AlertStore
from src.api.billing_store import BillingStore
from src.api.contract_store import ContractStore
from src.api.store_factory import build_stores
from src.api.store_persistence import Persister
from src.api.tenant_state_store import TenantStateStore
from src.api.tenant_user_store import TenantUserStore
from src.api.watch_store import WatchStore


class _FakePersister:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, str]] = []

    def upsert(self, table: str, pk: dict, data_json: str) -> None:
        self.calls.append((table, pk, data_json))


def _fake_pool(rows_by_table: dict[str, list[dict]]):
    pool = MagicMock()

    async def _fetch(query: str, *args):
        for table, rows in rows_by_table.items():
            if f"FROM {table}" in query:
                return rows
        return []

    pool.fetch = AsyncMock(side_effect=_fetch)
    return pool


# ── AT-002: sem pool → tudo in-memory, comportamento histórico ───────────────


def test_build_stores_sem_pool_retorna_in_memory():
    stores = build_stores(None)
    assert isinstance(stores.contracts, ContractStore)
    assert isinstance(stores.billing, BillingStore)
    assert isinstance(stores.alerts, AlertStore)
    assert isinstance(stores.watch, WatchStore)
    assert isinstance(stores.tenant_users, TenantUserStore)
    assert isinstance(stores.tenant_states, TenantStateStore)
    assert isinstance(stores.admin_audit, AdminAuditStore)
    assert stores.persister is None


@pytest.mark.asyncio
async def test_hydrate_sem_pool_e_noop():
    stores = build_stores(None)
    await stores.hydrate(None)
    await stores.aclose()


def test_build_stores_com_pool_usa_alloydb():
    from src.api.stores_db import AlloyDBContractStore
    stores = build_stores(MagicMock())
    assert isinstance(stores.contracts, AlloyDBContractStore)
    assert stores.tenant_users._persister is stores.persister


# ── write-through: mutações enfileiram upsert ─────────────────────────────────


def test_tenant_user_store_write_through():
    p = _FakePersister()
    store = TenantUserStore(persister=p)
    m = store.create_member("t1", "uid1", "a@b.com")
    store.revoke_member("t1", m.id)
    inv = store.create_invite("t1", "x@y.com")
    store.accept_invite(inv.token)
    store.update_notif_prefs("t1", email_enabled=False)
    tables = [c[0] for c in p.calls]
    assert tables.count("tenant_members") == 2
    assert tables.count("tenant_invites") == 2
    assert tables.count("tenant_notif_prefs") == 1


def test_tenant_state_store_write_through():
    p = _FakePersister()
    store = TenantStateStore(persister=p)
    store.block("t1", "fraude", "admin@x.com")
    store.unblock("t1")
    store.create_impersonation("tok", "t1", "admin@x.com", "2099-01-01T00:00:00+00:00")
    assert [c[0] for c in p.calls] == ["tenant_states", "tenant_states", "impersonation_tokens"]


def test_admin_audit_write_through():
    p = _FakePersister()
    store = AdminAuditStore(persister=p)
    store.append("admin@x.com", "block_tenant", entidade_id="t1")
    assert p.calls[0][0] == "admin_audit"
    assert json.loads(p.calls[0][2])["acao"] == "block_tenant"


def test_sem_persister_mantem_comportamento_atual():
    store = TenantUserStore()
    m = store.create_member("t1", "uid1", "a@b.com")
    assert store.get_member_by_uid("t1", "uid1") == m


# ── hydrate popula dicts a partir do banco ────────────────────────────────────


@pytest.mark.asyncio
async def test_hydrate_tenant_users():
    member_json = TenantUserStore().create_member("t1", "uid1", "a@b.com").model_dump_json()
    pool = _fake_pool({"tenant_members": [{"data": member_json}]})
    store = TenantUserStore()
    await store.hydrate(pool)
    assert store.get_member_by_uid("t1", "uid1") is not None


@pytest.mark.asyncio
async def test_hydrate_tenant_states_filtra_impersonation_expirada():
    from src.api.tenant_state_store import ImpersonationToken, TenantState
    state_json = TenantState(tenant_id="t1", blocked=True).model_dump_json()
    expired = ImpersonationToken(
        token="old", tenant_id="t1", admin_email="a@x.com",
        expires_at="2020-01-01T00:00:00+00:00",
    ).model_dump_json()
    pool = _fake_pool({
        "tenant_states": [{"data": state_json}],
        "impersonation_tokens": [{"data": expired}],
    })
    store = TenantStateStore()
    await store.hydrate(pool)
    assert store.is_blocked("t1") is True
    assert store.get_impersonation("old") is None


# ── persister: flush em lote e shutdown drena fila ────────────────────────────


@pytest.mark.asyncio
async def test_persister_flush_e_aclose():
    executed: list[tuple] = []
    conn = MagicMock()

    async def _execute(q, *args):
        executed.append((q, args))

    conn.execute = AsyncMock(side_effect=_execute)
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)

    p = Persister(pool)
    p.upsert("tenant_states", {"tenant_id": "t1"}, '{"x":1}')
    p.upsert("tenant_states", {"tenant_id": "t2"}, '{"x":2}')
    await asyncio.sleep(0)
    await p.aclose()
    assert len(executed) == 2
    assert "ON CONFLICT (tenant_id)" in executed[0][0]
