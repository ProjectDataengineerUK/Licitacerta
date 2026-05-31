"""NOTIFICACOES_MULTICANAL — endpoints GET /alerts e POST /alerts/mark-read."""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.alert_store import AlertCreate, AlertStore
from src.api.deps import get_alert_store
from src.api.main import create_app


@pytest_asyncio.fixture()
async def aclient():
    app = create_app()
    store = AlertStore()
    app.dependency_overrides[get_alert_store] = lambda: store
    app.state.alert_store = store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, store


async def test_at006_pagination_filtro_lido(aclient):
    ac, store = aclient
    for i in range(50):
        a = await store.create(AlertCreate(tenant_id="t1", tipo="x", titulo=f"a{i}"))
        if i >= 30:  # 20 lidos, 30 não lidos
            await store.mark_read([a.id])

    resp = await ac.get("/alerts?lido=false&page=1&page_size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 20
    assert all(a["lido"] is False for a in body)


async def test_at007_mark_read(aclient):
    ac, store = aclient
    ids = []
    for i in range(5):
        a = await store.create(AlertCreate(tenant_id="t1", tipo="x", titulo=f"a{i}"))
        ids.append(a.id)

    resp = await ac.post("/alerts/mark-read", json={"ids": ids[:2]})
    assert resp.status_code == 200
    assert resp.json()["marked"] == 2

    nao_lidos = (await ac.get("/alerts?lido=false")).json()
    assert len(nao_lidos) == 3


async def test_filtro_severidade(aclient):
    ac, store = aclient
    await store.create(AlertCreate(tenant_id="t1", tipo="x", titulo="info", severidade="info"))
    await store.create(AlertCreate(tenant_id="t1", tipo="x", titulo="crit", severidade="critical"))

    criticos = (await ac.get("/alerts?severidade=critical")).json()
    assert len(criticos) == 1
    assert criticos[0]["severidade"] == "critical"
