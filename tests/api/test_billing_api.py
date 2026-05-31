"""BILLING_TENANT — endpoints /billing."""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.billing_store import BillingStore
from src.api.deps import get_billing_store
from src.api.main import create_app


@pytest_asyncio.fixture()
async def bclient():
    app = create_app()
    store = BillingStore()
    app.dependency_overrides[get_billing_store] = lambda: store
    app.state.billing_store = store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, store


async def test_list_plans(bclient):
    ac, _ = bclient
    plans = (await ac.get("/billing/plans")).json()
    nomes = {p["nome"] for p in plans}
    assert {"starter", "profissional", "business", "enterprise"} <= nomes
    assert "trial" not in nomes


async def test_usage_cria_trial(bclient):
    ac, store = bclient
    body = (await ac.get("/billing/usage?tenant_id=t1")).json()
    assert body["plan"] == "trial"
    assert body["subscription_status"] == "trial"
    assert body["limite"] == 10


async def test_webhook_ativa_via_metadata(bclient):
    ac, store = bclient
    await store.create_trial("t1")
    event = {
        "type": "invoice.paid",
        "data": {"object": {"metadata": {"tenant_id": "t1", "plan": "business"}, "subscription": "sub_9"}},
    }
    resp = await ac.post("/billing/webhook", json=event)
    assert resp.status_code == 200
    assert resp.json()["subscription_status"] == "active"
    assert (await store.get("t1")).plan == "business"


async def test_webhook_tenant_desconhecido_404(bclient):
    ac, _ = bclient
    event = {"type": "invoice.paid", "data": {"object": {"subscription": "sub_inexistente"}}}
    resp = await ac.post("/billing/webhook", json=event)
    assert resp.status_code == 404


async def test_checkout_stub_sem_stripe(bclient, monkeypatch):
    ac, _ = bclient
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    resp = await ac.post("/billing/checkout?tenant_id=t1&plan=profissional")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stripe_not_configured"
