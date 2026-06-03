"""SCORE_SAUDE_OPERACAO — testes de integração do endpoint GET /health-score.

Padrão: cria app via create_app(), sobrescreve get_store e get_contract_store
com stores vazios, usa ASGITransport. Sem @pytest.mark.asyncio (asyncio_mode=auto).
"""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.contract_store import ContractStore
from src.api.deps import get_contract_store, get_store
from src.api.main import create_app
from src.api.store import RunStore


@pytest_asyncio.fixture()
async def health_client():
    app = create_app()
    store = RunStore()
    contracts = ContractStore()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_contract_store] = lambda: contracts
    app.state.store = store
    app.state.contract_store = contracts
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_health_score_endpoint_retorna_estrutura_completa(health_client):
    resp = await health_client.get("/health-score")

    assert resp.status_code == 200, f"Esperado 200, obtido {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "score" in body, "Chave 'score' ausente na resposta"
    assert "label" in body, "Chave 'label' ausente na resposta"
    assert "componentes" in body, "Chave 'componentes' ausente na resposta"
    assert len(body["componentes"]) == 6, (
        f"Esperados 6 componentes, obtidos {len(body['componentes'])}"
    )
