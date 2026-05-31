"""GESTAO_CONTRATOS_FULL — cálculo de reajuste via IBGE (AT-002)."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient, MockTransport, Response

from src.services.reajuste import ReajusteService


def _ibge_payload(serie: dict[str, str]) -> bytes:
    return json.dumps([
        {"id": "63", "variavel": "Variação mensal", "unidade": "%",
         "resultados": [{"classificacoes": [], "series": [{"localidade": {}, "serie": serie}]}]}
    ]).encode()


def _transport(serie: dict[str, str]) -> MockTransport:
    return MockTransport(lambda req: Response(200, content=_ibge_payload(serie)))


@pytest.mark.asyncio
async def test_at002_reajuste_compoe_variacao_mensal():
    # 2,0% e 3,0% compõem (1.02 * 1.03 - 1) = 5,06%
    serie = {"202602": "2.0", "202603": "3.0"}
    svc = ReajusteService(client=AsyncClient(transport=_transport(serie)))
    async with svc:
        r = await svc.calcular(Decimal("120000"), "IPCA", date(2026, 1, 1), date(2026, 3, 31))
    assert r.variacao_pct == pytest.approx(5.06, abs=1e-2)
    assert r.novo_valor_brl == Decimal("126072.00")
    assert r.indice == "IPCA"


@pytest.mark.asyncio
async def test_reajuste_ignora_meses_fora_do_intervalo():
    # 202601 == data_base (não conta); só 202602 entra
    serie = {"202601": "10.0", "202602": "1.0"}
    svc = ReajusteService(client=AsyncClient(transport=_transport(serie)))
    async with svc:
        r = await svc.calcular(Decimal("1000"), "IPCA", date(2026, 1, 1), date(2026, 2, 28))
    assert r.novo_valor_brl == Decimal("1010.00")


@pytest.mark.asyncio
async def test_reajuste_indice_nao_suportado():
    svc = ReajusteService(client=AsyncClient(transport=_transport({})))
    async with svc:
        with pytest.raises(ValueError, match="não suportado"):
            await svc.calcular(Decimal("1000"), "IGPM", date(2026, 1, 1), date(2026, 6, 1))


@pytest.mark.asyncio
async def test_reajuste_data_invalida():
    svc = ReajusteService(client=AsyncClient(transport=_transport({})))
    async with svc:
        with pytest.raises(ValueError, match="posterior"):
            await svc.calcular(Decimal("1000"), "IPCA", date(2026, 6, 1), date(2026, 1, 1))


@pytest.mark.asyncio
async def test_reajuste_usa_cache(monkeypatch):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return Response(200, content=_ibge_payload({"202602": "1.0"}))

    svc = ReajusteService(client=AsyncClient(transport=MockTransport(handler)))
    async with svc:
        await svc.calcular(Decimal("1000"), "IPCA", date(2026, 1, 1), date(2026, 2, 28))
        await svc.calcular(Decimal("2000"), "IPCA", date(2026, 1, 1), date(2026, 2, 28))
    assert calls["n"] == 1  # segunda chamada veio do cache
