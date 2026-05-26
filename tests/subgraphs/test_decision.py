from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.graph.state import initial_state
from src.schemas.results import (
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    PricingResult,
)
from src.schemas.tender import TenderSchema


def _make_pricing() -> PricingResult:
    return PricingResult(
        conclusion="Margem adequada para participação.",
        confidence=0.85,
        cost_estimate=Decimal("80000.00"),
        min_margin_pct=18.0,
        recommended_price=Decimal("97560.98"),
        scenarios={
            "pessimista": Decimal("88888.89"),
            "realista": Decimal("97560.98"),
            "otimista": Decimal("106666.67"),
        },
        recommended_action="Usar preço realista",
    )


def _make_bid_decision(rec: str = "participar") -> BidDecision:
    return BidDecision(
        conclusion="Condições favoráveis para participação.",
        confidence=0.88,
        recommendation=rec,
        risk_level="low",
        expected_margin_pct=18.0,
        recommended_action="Participar com preço realista",
    )


def _base_state():
    state = initial_state("edital-dec-001", "texto", "12345678000195")
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
    )
    state["eligibility"] = EligibilityResult(
        conclusion="Elegível", confidence=0.9, is_eligible=True, recommended_action="ok"
    )
    state["compliance"] = ComplianceResult(
        conclusion="Baixo risco", confidence=0.9, risk_level="low", recommended_action="ok"
    )
    state["blacklist"] = BlacklistResult(
        ceis_blocked=False, cnep_blocked=False, cepim_blocked=False,
        any_blocked=False, checked_at=datetime.utcnow()
    )
    return state


@pytest.fixture()
def decision_graph_with_mocks():
    mock_pricing = MagicMock()
    mock_pricing.run.return_value = _make_pricing()
    mock_bid = MagicMock()
    mock_bid.run.return_value = _make_bid_decision()

    with (
        patch("src.graph.subgraphs.decision.PricingAgent", return_value=mock_pricing),
        patch("src.graph.subgraphs.decision.BidNoBidAgent", return_value=mock_bid),
    ):
        from src.graph.subgraphs.decision import build_decision_subgraph
        graph = build_decision_subgraph()
        yield graph, mock_pricing, mock_bid


async def test_decision_happy_path(decision_graph_with_mocks):
    graph, _, _ = decision_graph_with_mocks
    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "decided"
    assert result["pricing"].recommended_price == Decimal("97560.98")
    assert result["bid_decision"].recommendation == "participar"
    assert result["bid_decision"].risk_level == "low"
    assert len(result["audit_log"]) == 2
    assert result["errors"] == []


async def test_decision_nao_participar(decision_graph_with_mocks):
    graph, _, mock_bid = decision_graph_with_mocks
    mock_bid.run.return_value = _make_bid_decision("nao_participar")

    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "decided"
    assert result["bid_decision"].recommendation == "nao_participar"


async def test_decision_pricing_error_continues(decision_graph_with_mocks):
    graph, mock_pricing, _ = decision_graph_with_mocks
    mock_pricing.run.side_effect = RuntimeError("modelo indisponível")

    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "decided"
    assert any(e.agent == "pricing" for e in result["errors"])
    # bid_no_bid ainda executa com pricing=None
    assert result["bid_decision"] is not None


async def test_decision_audit_log_order(decision_graph_with_mocks):
    graph, _, _ = decision_graph_with_mocks
    result = await graph.ainvoke(_base_state())

    agents = [e.agent for e in result["audit_log"]]
    assert agents == ["pricing", "bid_no_bid"]


async def test_decision_context_minimum(decision_graph_with_mocks):
    """Pricing recebe apenas os campos necessários (ADR-002)."""
    graph, mock_pricing, _ = decision_graph_with_mocks
    await graph.ainvoke(_base_state())

    ctx = mock_pricing.run.call_args[0][0]
    assert "tender_schema" in ctx
    assert "eligibility" in ctx
    assert "compliance" in ctx
    assert "blacklist" in ctx
    assert "company_cnpj" in ctx
    assert "edital_pages" not in ctx


async def test_decision_audit_log_model_used(decision_graph_with_mocks):
    graph, _, _ = decision_graph_with_mocks
    result = await graph.ainvoke(_base_state())

    pricing_event = next(e for e in result["audit_log"] if e.agent == "pricing")
    bid_event = next(e for e in result["audit_log"] if e.agent == "bid_no_bid")
    assert pricing_event.model_used == settings.gemini_pro
    assert bid_event.model_used == settings.gemini_pro
