"""PERSISTENCIA_STORES — AT-001..AT-006 contra Postgres real.

Requer DATABASE_URL (ex.: docker run -e POSTGRES_PASSWORD=pg -p 5432:5432 postgres:16
e DATABASE_URL=postgresql://postgres:pg@localhost:5432/postgres).
Aplica migrations 021–027 antes; roda com: pytest -m integration
"""
from __future__ import annotations

import os
import pathlib
import uuid

import pytest

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MIGRATIONS = pathlib.Path(__file__).parents[2] / "scripts" / "migrations"


@pytest.fixture()
async def pool():
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL não configurada")
    import asyncpg
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        for mig in sorted(MIGRATIONS.glob("02[1-7]_*.sql")):
            await conn.execute(mig.read_text())
    yield pool
    await pool.close()


async def test_at001_contrato_sobrevive_restart(pool):
    from datetime import date, timedelta

    from src.api.contract_store import ContractCreate
    from src.api.stores_db import AlloyDBContractStore

    store1 = AlloyDBContractStore(pool)
    c = await store1.create(
        ContractCreate(
            orgao_cnpj="00000000000191",
            valor_original_brl=50000.0,
            data_inicio=date.today(),
            data_vencimento=date.today() + timedelta(days=365),
        ),
        tenant_id=f"t-{uuid.uuid4()}",
    )
    store2 = AlloyDBContractStore(pool)  # simula novo processo
    got = await store2.get(c.id)
    assert got is not None
    assert got.valor_atual_brl == 50000.0
    emp = await store2.add_empenho(
        c.id, __import__("src.api.contract_store", fromlist=["EmpenhoCreate"]).EmpenhoCreate(
            numero_empenho="NE1", valor_brl=100.0, data_emissao=date.today()
        )
    )
    assert emp is not None
    assert len((await store2.get(c.id)).empenhos) == 1


async def test_at003_membership_sobrevive_restart(pool):
    from src.api.store_persistence import Persister
    from src.api.tenant_user_store import TenantUserStore

    tid = f"t-{uuid.uuid4()}"
    p = Persister(pool)
    store1 = TenantUserStore(persister=p)
    store1.create_member(tid, "uid-1", "a@b.com", papel="operator")
    inv = store1.create_invite(tid, "x@y.com")
    store1.accept_invite(inv.token)
    await p.aclose()  # flush

    store2 = TenantUserStore()
    await store2.hydrate(pool)
    m = store2.get_member_by_uid(tid, "uid-1")
    assert m is not None and m.papel == "operator"
    assert store2.get_invite_by_token(inv.token).is_accepted()


async def test_at004_billing_sobrevive_restart(pool):
    from src.api.billing_store import TenantBilling
    from src.api.stores_db import AlloyDBBillingStore

    tid = f"t-{uuid.uuid4()}"
    store1 = AlloyDBBillingStore(pool)
    await store1.set(TenantBilling(
        tenant_id=tid, plan="profissional", subscription_status="active",
        stripe_customer_id="cus_x", stripe_subscription_id=f"sub_{tid}",
    ))
    store2 = AlloyDBBillingStore(pool)
    b = await store2.get_by_subscription_id(f"sub_{tid}")
    assert b is not None
    assert b.plan == "profissional"


async def test_at005_rls_isola_tenants(pool):
    from src.api.alert_store import AlertCreate
    from src.api.stores_db import AlloyDBAlertStore

    ta, tb = f"ta-{uuid.uuid4()}", f"tb-{uuid.uuid4()}"
    store = AlloyDBAlertStore(pool)
    await store.create(AlertCreate(tenant_id=ta, tipo="x", titulo="A"))
    await store.create(AlertCreate(tenant_id=tb, tipo="x", titulo="B"))
    # filtro explícito de tenant (defesa primária da aplicação)
    only_a = await store.query(tenant_id=ta)
    assert {a.tenant_id for a in only_a} == {ta}
    # RLS (defesa em profundidade) — exige role sem BYPASSRLS
    async with pool.acquire() as conn:
        is_super = await conn.fetchval("SELECT current_setting('is_superuser')")
        if is_super == "on":
            pytest.skip("superuser ignora RLS — validar com role de aplicação")
        await conn.execute(f"SET app.tenant_id = '{ta}'")
        rows = await conn.fetch("SELECT tenant_id FROM alerts WHERE tenant_id=$1", tb)
        assert rows == []


async def test_at006_admin_audit_append_only(pool):
    from src.api.admin_audit_store import AdminAuditStore
    from src.api.store_persistence import Persister

    p = Persister(pool)
    store1 = AdminAuditStore(persister=p)
    for i in range(3):
        store1.append("admin@x.com", f"acao_{i}")
    await p.aclose()

    store2 = AdminAuditStore()
    await store2.hydrate(pool)
    acoes = [e.acao for e in store2.list(admin_email="admin@x.com", limit=3)]
    assert len(acoes) == 3


async def test_watch_dedup_sobrevive_restart(pool):
    from src.api.stores_db import AlloyDBWatchStore

    store1 = AlloyDBWatchStore(pool)
    cfg = await store1.create_config(["notebook"], "00000000000191")
    pid = f"pncp-{uuid.uuid4()}"
    await store1.record(pid, cfg.id, "run-1")
    store2 = AlloyDBWatchStore(pool)
    assert await store2.is_seen(pid) is True
    assert any(c.id == cfg.id for c in await store2.list_configs())
