"""DASHBOARD_COCKPIT_V2 — summary KPIs, pipeline Kanban e PATCH de stage.

Popula um RunStore diretamente para asserções determinísticas das agregações.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.deps import get_store
from src.api.main import create_app
from src.api.store import RunStore


def _snapshot(
    *,
    edital_id: str = "ED-1",
    current_step: str = "validated",
    valor: float | None = None,
    data_encerramento: str | None = None,
    confidence: float | None = None,
    errors: list | None = None,
) -> dict:
    snap: dict = {"edital_id": edital_id, "current_step": current_step, "errors": errors or []}
    tender: dict = {"orgao": "Prefeitura X", "objeto": "Obra Y"}
    if valor is not None:
        tender["valor_estimado"] = valor
    if data_encerramento is not None:
        tender["data_encerramento"] = data_encerramento
    snap["tender_schema"] = tender
    if confidence is not None:
        snap["bid_decision"] = {"recommendation": "participar", "confidence": confidence}
    return snap


@pytest_asyncio.fixture()
async def dash():
    app = create_app()
    store = RunStore()
    app.dependency_overrides[get_store] = lambda: store
    app.state.store = store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, store


async def test_at001_summary_counts_by_stage(dash):
    ac, store = dash
    await store.create("r1", _snapshot(current_step="validated"))   # analisando
    await store.create("r2", _snapshot(current_step="decided"))     # decidindo
    await store.create("r3", _snapshot(current_step="completed"))   # preparando

    resp = await ac.get("/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pipeline"]["analisando"] == 1
    assert body["pipeline"]["decidindo"] == 1
    assert body["pipeline"]["preparando"] == 1
    # run aguardando decisão humana conta como alerta crítico
    assert body["alertas_criticos"] == 1


async def test_taxa_vitoria_ganho_perdido(dash):
    ac, store = dash
    await store.create("g", _snapshot())
    await store.create("p", _snapshot())
    await store.set_stage("g", "ganho")
    await store.set_stage("p", "perdido")

    body = (await ac.get("/dashboard/summary")).json()
    assert body["pipeline"]["ganho_mes"] == 1
    assert body["pipeline"]["perdido_mes"] == 1
    assert body["taxa_vitoria_pct"] == 50.0


async def test_financeiro_receita_e_a_receber(dash):
    ac, store = dash
    perto = (date.today() + timedelta(days=20)).isoformat()
    medio = (date.today() + timedelta(days=45)).isoformat()
    await store.create("g1", _snapshot(valor=50000.0, data_encerramento=perto))
    await store.create("g2", _snapshot(valor=30000.0, data_encerramento=medio))
    await store.set_stage("g1", "ganho")
    await store.set_stage("g2", "ganho")

    fin = (await ac.get("/dashboard/summary")).json()["financeiro"]
    assert fin["receita_contratada_brl"] == 80000.0
    assert fin["a_receber_30d_brl"] == 50000.0
    assert fin["a_receber_60d_brl"] == 30000.0


async def test_summary_warning_counts_errors(dash):
    ac, store = dash
    await store.create("e1", _snapshot(errors=[{"message": "boom"}]))
    body = (await ac.get("/dashboard/summary")).json()
    assert body["alertas_warning"] == 1


async def test_pipeline_lists_items_with_derived_stage(dash):
    ac, store = dash
    await store.create("r1", _snapshot(current_step="decided", valor=12345.0, confidence=0.78))

    items = (await ac.get("/pipeline")).json()
    assert len(items) == 1
    item = items[0]
    assert item["run_id"] == "r1"
    assert item["stage"] == "decidindo"
    assert item["bid_score"] == 0.78
    assert item["valor_estimado_brl"] == 12345.0
    assert item["orgao"] == "Prefeitura X"


async def test_at003_patch_stage_moves_card(dash):
    ac, store = dash
    await store.create("r1", _snapshot(current_step="validated"))

    resp = await ac.patch("/pipeline/r1/stage", json={"stage": "ganho"})
    assert resp.status_code == 200
    assert resp.json()["stage"] == "ganho"

    body = (await ac.get("/dashboard/summary")).json()
    assert body["pipeline"]["ganho_mes"] == 1
    assert body["pipeline"]["analisando"] == 0


async def test_patch_unknown_run_returns_404(dash):
    ac, _ = dash
    resp = await ac.patch("/pipeline/nope/stage", json={"stage": "ganho"})
    assert resp.status_code == 404


async def test_patch_invalid_stage_returns_422(dash):
    ac, store = dash
    await store.create("r1", _snapshot())
    resp = await ac.patch("/pipeline/r1/stage", json={"stage": "inexistente"})
    assert resp.status_code == 422
