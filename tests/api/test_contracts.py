"""GESTAO_CONTRATOS_FULL — CRUD, empenhos, SRP, dashboard, alertas, reajuste."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient, MockTransport, Response

from src.api.contract_store import ContractStore
from src.api.deps import get_contract_store, get_reajuste_service
from src.api.main import create_app
from src.services.reajuste import ReajusteService


def _ibge_transport(serie: dict[str, str]) -> MockTransport:
    payload = json.dumps([
        {"id": "63", "resultados": [{"series": [{"serie": serie}]}]}
    ]).encode()
    return MockTransport(lambda req: Response(200, content=payload))


@pytest_asyncio.fixture()
async def cclient():
    app = create_app()
    store = ContractStore()
    app.dependency_overrides[get_contract_store] = lambda: store
    app.dependency_overrides[get_reajuste_service] = lambda: ReajusteService(
        client=AsyncClient(transport=_ibge_transport({"202602": "2.0", "202603": "3.0"}))
    )
    app.state.contract_store = store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _contract_body(**over) -> dict:
    body = {
        "orgao_cnpj": "00000000000191",
        "orgao_nome": "Prefeitura X",
        "objeto": "serviços de TI",
        "valor_original_brl": 120000.0,
        "indice_reajuste": "IPCA",
        "data_base": "2026-01-01",
        "data_inicio": "2026-01-01",
        "data_vencimento": (date.today() + timedelta(days=365)).isoformat(),
        "prazo_pagamento_dias": 30,
    }
    body.update(over)
    return body


async def test_at001_create_contract(cclient: AsyncClient):
    resp = await cclient.post("/contracts", json=_contract_body())
    assert resp.status_code == 201
    c = resp.json()
    assert c["indice_reajuste"] == "IPCA"
    assert c["data_base"] == "2026-01-01"
    assert c["valor_atual_brl"] == 120000.0
    assert c["status"] == "ativo"


async def test_get_and_list_and_404(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body())).json()["id"]
    assert (await cclient.get(f"/contracts/{cid}")).status_code == 200
    assert len((await cclient.get("/contracts")).json()) == 1
    assert (await cclient.get("/contracts/nope")).status_code == 404


async def test_at004_srp_saldo(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body(
        tipo="ata_srp", srp_quantidade_registrada=100.0))).json()["id"]
    await cclient.post(
        f"/contracts/{cid}/srp",
        json={"numero_convocacao": "C1", "quantidade": 30.0, "status": "atendida"},
    )
    await cclient.post(
        f"/contracts/{cid}/srp",
        json={"numero_convocacao": "C2", "quantidade": 20.0, "status": "atendida"},
    )

    c = (await cclient.get(f"/contracts/{cid}")).json()
    assert c["saldo_srp"] == 50.0


async def test_at005_empenho_pago_e_dashboard(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body())).json()["id"]
    eid = (await cclient.post(f"/contracts/{cid}/empenhos", json={
        "numero_empenho": "2026NE001", "valor_brl": 50000.0, "data_emissao": date.today().isoformat()
    })).json()["id"]

    resp = await cclient.patch(f"/contracts/{cid}/empenhos/{eid}", json={
        "status": "pago", "data_pagamento": date.today().isoformat()})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pago"

    dash = (await cclient.get("/contracts/dashboard")).json()
    assert dash["recebido_brl"] == 50000.0
    assert dash["total_contratado_brl"] == 120000.0


async def test_at003_alerta_vencimento(cclient: AsyncClient):
    await cclient.post("/contracts", json=_contract_body(
        data_vencimento=(date.today() + timedelta(days=25)).isoformat()))
    alerts = (await cclient.get("/contracts/alerts")).json()
    venc = [a for a in alerts if a["tipo"] == "vencimento_contrato"]
    assert len(venc) == 1
    assert venc[0]["severity"] == "warning"


async def test_at006_alerta_pagamento_atrasado(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body())).json()["id"]
    await cclient.post(f"/contracts/{cid}/empenhos", json={
        "numero_empenho": "2026NE002", "valor_brl": 10000.0,
        "data_emissao": (date.today() - timedelta(days=45)).isoformat()})

    alerts = (await cclient.get("/contracts/alerts")).json()
    atraso = [a for a in alerts if a["tipo"] == "pagamento_atrasado"]
    assert len(atraso) == 1
    assert atraso[0]["severity"] == "critical"


async def test_at002_reajuste_endpoint(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body())).json()["id"]
    resp = await cclient.get(f"/contracts/{cid}/reajuste?data_reajuste=2026-03-31")
    assert resp.status_code == 200
    body = resp.json()
    # 2% e 3% → 5,06% sobre 120000 = 126072.00
    assert body["novo_valor_brl"] == 126072.00
    assert round(body["variacao_pct"], 2) == 5.06


async def test_delete_soft(cclient: AsyncClient):
    cid = (await cclient.post("/contracts", json=_contract_body())).json()["id"]
    assert (await cclient.delete(f"/contracts/{cid}")).status_code == 204
    assert (await cclient.get(f"/contracts/{cid}")).json()["status"] == "encerrado"
