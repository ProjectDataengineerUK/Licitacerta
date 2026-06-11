from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.graph.state import initial_state
from src.graph.subgraphs.decision import should_impugnar
from src.schemas.results import (
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    ImpugnacaoResult,
    Issue,
    PricingResult,
)
from src.schemas.tender import TenderSchema
from src.utils.business_days import subtract_business_days


def _make_pricing() -> PricingResult:
    return PricingResult(
        conclusion="ok",
        confidence=0.85,
        cost_estimate=Decimal("80000.00"),
        min_margin_pct=18.0,
        recommended_price=Decimal("97560.98"),
        scenarios={"realista": Decimal("97560.98")},
        recommended_action="ok",
    )


def _make_bid(rec: str = "participar") -> BidDecision:
    return BidDecision(
        conclusion="ok",
        confidence=0.88,
        recommendation=rec,
        risk_level="low",
        expected_margin_pct=18.0,
        recommended_action=rec,
    )


def _make_compliance(risk: str = "low", blocking: bool = False) -> ComplianceResult:
    issues = []
    if blocking:
        issues = [Issue(description="cláusula restritiva", severity="blocking")]
    return ComplianceResult(
        conclusion="ok",
        confidence=0.9,
        risk_level=risk,
        blocking_issues=issues,
        recommended_action="ok",
    )


def _state(bid_rec: str = "participar", risk: str = "low", blocking: bool = False):
    state = initial_state("edital-imp-001", "texto", "12345678000195")
    state["tender_schema"] = TenderSchema(
        objeto="Serviços de TI",
        orgao="TCU",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ"],
        exigencias_tecnicas=[],
        penalidades=[],
        evidence=[],
        valor_estimado=Decimal("100000.00"),
        prazo_pagamento_dias=30,
        data_abertura=date(2026, 6, 10),
    )
    state["eligibility"] = EligibilityResult(
        conclusion="ok", confidence=0.9, is_eligible=True, recommended_action="ok"
    )
    state["compliance"] = _make_compliance(risk, blocking)
    state["blacklist"] = BlacklistResult(
        ceis_blocked=False, cnep_blocked=False, cepim_blocked=False,
        any_blocked=False, checked_at=datetime.utcnow(),
    )
    return state


def _make_impugnacao(rec: str = "impugnar") -> ImpugnacaoResult:
    return ImpugnacaoResult(
        conclusion="Cláusula de alto risco identificada.",
        confidence=0.9,
        recommended_action=rec,
        recommendation=rec,
        prazo_limite=date(2026, 6, 5),
        human_decision_required=False,
    )


@pytest.fixture()
def graph_with_mocks():
    mock_pricing = MagicMock()
    mock_pricing.run.return_value = _make_pricing()
    mock_pricing.get_last_metric.return_value = None
    mock_bid = MagicMock()
    mock_bid.run.return_value = _make_bid()
    mock_bid.get_last_metric.return_value = None
    mock_imp = MagicMock()

    async def _arun(ctx):
        return _make_impugnacao()

    mock_imp.arun = _arun
    mock_imp.get_last_metric.return_value = None

    mock_market = MagicMock()

    async def _mi_arun(ctx):
        from src.schemas.market import CompetitiveContext
        return CompetitiveContext(
            data_insuficiente=True,
            resumo="Dados de mercado insuficientes para análise competitiva.",
        )

    mock_market.arun = _mi_arun
    mock_market.get_last_metric.return_value = None

    mock_estrategia = MagicMock()

    async def _est_arun(ctx):
        from src.schemas.estrategia import EstrategiaResult
        return EstrategiaResult(
            probabilidade_sem_acoes_pct=50.0,
            probabilidade_com_acoes_pct=65.0,
            acoes=[],
            resumo_executivo="Sem ações adicionais.",
        )

    mock_estrategia.arun = _est_arun
    mock_estrategia.get_last_metric.return_value = None

    with (
        patch("src.graph.subgraphs.decision.MarketIntelAgent", return_value=mock_market),
        patch("src.graph.subgraphs.decision.EstrategiaAgent", return_value=mock_estrategia),
        patch("src.graph.subgraphs.decision.PricingAgent", return_value=mock_pricing),
        patch("src.graph.subgraphs.decision.BidNoBidAgent", return_value=mock_bid),
        patch("src.graph.subgraphs.decision.ImpugnacaoAgent", return_value=mock_imp),
    ):
        from src.graph.subgraphs.decision import build_decision_subgraph

        graph = build_decision_subgraph()
        yield graph, mock_bid


async def test_at001_ativacao_por_bid_impugnar(graph_with_mocks):
    graph, mock_bid = graph_with_mocks
    mock_bid.run.return_value = _make_bid("impugnar")

    result = await graph.ainvoke(_state(bid_rec="impugnar"))

    assert result["impugnacao"] is not None
    assert result["impugnacao"].recommendation == "impugnar"


async def test_at002_ativacao_por_compliance_critico(graph_with_mocks):
    graph, _ = graph_with_mocks

    result = await graph.ainvoke(_state(bid_rec="participar", risk="critical"))

    assert result["impugnacao"] is not None


async def test_at003_nao_ativado_edital_limpo(graph_with_mocks):
    graph, _ = graph_with_mocks

    result = await graph.ainvoke(_state(bid_rec="participar", risk="low"))

    assert result["impugnacao"] is None


async def test_at004_hitl_sempre_obrigatorio(graph_with_mocks):
    graph, _ = graph_with_mocks

    result = await graph.ainvoke(_state(bid_rec="participar", risk="critical"))

    assert result["impugnacao"].human_decision_required is True


def test_at005_prazo_impugnacao_3_dias_uteis():
    assert subtract_business_days(date(2026, 6, 10), 3) == date(2026, 6, 5)


def test_at006_should_impugnar_por_blocking_issue():
    assert should_impugnar(_state(bid_rec="participar", risk="medium", blocking=True)) is True


def test_should_impugnar_edital_limpo_false():
    assert should_impugnar(_state(bid_rec="participar", risk="low")) is False


def test_should_impugnar_compliance_none_false():
    state = initial_state("x", "y", "12345678000195")
    state["bid_decision"] = _make_bid("participar")
    assert should_impugnar(state) is False


async def test_api_runresult_inclui_impugnacao():
    from src.api.store import RunStore

    store = RunStore()
    run_id = "run-imp-001"
    await store.create(run_id, {"edital_id": "edital-imp-001", "impugnacao": _make_impugnacao()})
    entry = await store.get(run_id)

    result = store.to_result(entry)
    assert result.impugnacao is not None
    assert result.impugnacao["recommendation"] == "impugnar"
