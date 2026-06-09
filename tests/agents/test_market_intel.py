"""Testes unitários para MarketIntelAgent (AT-001, AT-002, AT-005, AT-006)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.market_intel import MarketIntelAgent
from src.schemas.market import CompetitiveContext, CompetitorProfile, OrganScore, PriceBenchmark


def _make_agent() -> MarketIntelAgent:
    agent = MarketIntelAgent.__new__(MarketIntelAgent)
    agent._bq = None
    agent._last_metric = None
    agent._metric_lock = __import__("threading").Lock()
    return agent


# ── AT-005: curto-circuito quando todos data_insuficiente ─────────────────────
@pytest.mark.asyncio
async def test_short_circuit_when_all_insuficiente():
    agent = _make_agent()
    agent._llm = AsyncMock()  # nunca deve ser chamado

    svc = AsyncMock()
    svc.competitor_xray.return_value = CompetitorProfile(
        cnpj="11111111000100", taxa_vitoria_pct=0, total_vitorias=0
    )
    svc.segment_summary.return_value = {"top_fornecedores": [], "concentracao_alta": False, "cnpj_dominante": None}
    svc.price_benchmark.return_value = PriceBenchmark(item_descricao="x", amostra=0, data_insuficiente=True)
    svc.organ_score.return_value = OrganScore(
        orgao_cnpj="", score=50, label="Regular", amostra=0, data_insuficiente=True
    )

    result = await agent.arun({
        "company_cnpj": "11111111000100",
        "segmento_cnae": "6201-5",
        "item_descricao": "notebook",
        "uasg": "123456",
        "service": svc,
    })

    assert result.data_insuficiente
    agent._llm.ainvoke.assert_not_called()


# ── AT-001: competitor_xray chamado e dados retornados ────────────────────────
@pytest.mark.asyncio
async def test_competitor_data_returned():
    agent = _make_agent()

    competitor = CompetitorProfile(
        cnpj="11111111000100",
        nome="Empresa X",
        taxa_vitoria_pct=35.0,
        total_vitorias=70,
        dominante=True,
    )
    benchmark = PriceBenchmark(
        item_descricao="notebook",
        amostra=20,
        media_brl=Decimal("3500"),
        percentil_75=Decimal("4200"),
    )
    organ = OrganScore(
        orgao_cnpj="00000000000100", score=80, label="Bom Pagador", amostra=15
    )

    svc = AsyncMock()
    svc.competitor_xray.return_value = competitor
    svc.segment_summary.return_value = {"top_fornecedores": [], "concentracao_alta": True, "cnpj_dominante": "11111111000100"}
    svc.price_benchmark.return_value = benchmark
    svc.organ_score.return_value = organ

    mock_result = CompetitiveContext(
        segmento_cnae="6201-5",
        concentracao_alta=True,
        resumo="Mercado concentrado por Empresa X.",
    )
    agent._llm = MagicMock()
    agent._llm.ainvoke = AsyncMock(return_value={"parsed": mock_result, "raw": None})

    result = await agent.arun({
        "company_cnpj": "11111111000100",
        "segmento_cnae": "6201-5",
        "item_descricao": "notebook",
        "uasg": "123456",
        "service": svc,
    })

    assert not result.data_insuficiente
    assert result.price_benchmark == benchmark
    assert result.organ_score == organ


# ── AT-006: benchmark p75 injetado no PricingAgent._build_messages ────────────
def test_pricing_agent_receives_benchmark():
    from src.agents.pricing import PricingAgent
    from src.schemas.market import CompetitiveContext, PriceBenchmark

    agent = PricingAgent.__new__(PricingAgent)

    cc = CompetitiveContext(
        price_benchmark=PriceBenchmark(
            item_descricao="notebook",
            amostra=20,
            media_brl=Decimal("3500"),
            percentil_75=Decimal("4200"),
            percentil_25=Decimal("3000"),
            data_insuficiente=False,
        ),
        resumo="Mercado moderadamente concentrado.",
        data_insuficiente=False,
    )

    messages = agent._build_messages({
        "tender_schema": None,
        "eligibility": None,
        "compliance": None,
        "blacklist": None,
        "company_cnpj": "11111111000100",
        "competitive_context": cc,
    })

    human_content = messages[1].content
    assert "4200" in human_content
    assert "benchmark_mercado_p75_brl" in human_content
    assert "Mercado moderadamente" in human_content
