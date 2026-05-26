from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.graph.state import initial_state
from src.schemas.results import BidDecision, HumanApproval, PricingResult, ProposalDraft
from src.schemas.tender import TenderSchema


def _make_proposal() -> ProposalDraft:
    return ProposalDraft(
        content="PROPOSTA COMERCIAL\n\nEmpresa: ACME LTDA\nCNPJ: 12.345.678/0001-95\n"
                "Objeto: Fornecimento de papel A4\nPreço Total: R$ 47.058,82\n"
                "Validade: 60 dias\nPrazo de entrega: 30 dias",
        attachments=["cnpj.pdf", "cnd_federal.pdf", "regularidade_fgts.pdf"],
        price=Decimal("47058.82"),
        validity_days=60,
        generated_at=datetime.utcnow(),
        approved_by="jonatas",
        approved_at=datetime.utcnow(),
    )


def _base_state():
    state = initial_state("edital-exec-001", "texto", "12345678000195")
    state["current_step"] = "approved"
    state["tender_schema"] = TenderSchema(
        objeto="Fornecimento de papel A4",
        orgao="Câmara Municipal",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ", "CND Federal", "FGTS"],
        exigencias_tecnicas=[],
        penalidades=[],
        evidence=[],
        prazo_pagamento_dias=30,
    )
    state["pricing"] = PricingResult(
        conclusion="Margem ok", confidence=0.85,
        cost_estimate=Decimal("40000.00"), min_margin_pct=15.0,
        recommended_price=Decimal("47058.82"),
        scenarios={"pessimista": Decimal("44444.00"), "realista": Decimal("47058.82"), "otimista": Decimal("53333.00")},
        recommended_action="Participar",
    )
    state["bid_decision"] = BidDecision(
        conclusion="Participar", confidence=0.88,
        recommendation="participar", risk_level="low",
        expected_margin_pct=15.0, recommended_action="Participar",
    )
    state["human_approvals"] = [
        HumanApproval(
            step="pre_proposal", decision="approved",
            comment="Aprovado.", approver="jonatas",
            timestamp=datetime.utcnow(),
        )
    ]
    return state


@pytest.fixture()
def execution_graph_with_mock():
    mock_proposal = MagicMock()
    mock_proposal.run.return_value = _make_proposal()

    with patch("src.graph.subgraphs.execution.ProposalAgent", return_value=mock_proposal):
        from src.graph.subgraphs.execution import build_execution_subgraph
        graph = build_execution_subgraph()
        yield graph, mock_proposal


async def test_execution_happy_path(execution_graph_with_mock):
    graph, _ = execution_graph_with_mock
    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "executed"
    assert result["proposal_draft"].price == Decimal("47058.82")
    assert result["proposal_draft"].validity_days == 60
    assert len(result["proposal_draft"].attachments) == 3
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].model_used == settings.gemini_generate
    assert result["errors"] == []


async def test_execution_error_is_not_recoverable(execution_graph_with_mock):
    graph, mock_proposal = execution_graph_with_mock
    mock_proposal.run.side_effect = RuntimeError("modelo indisponível")

    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "execution_failed"
    assert len(result["errors"]) == 1
    assert result["errors"][0].recoverable is False


async def test_execution_uses_gemini_generate_model(execution_graph_with_mock):
    graph, _ = execution_graph_with_mock
    result = await graph.ainvoke(_base_state())

    assert result["audit_log"][0].model_used == settings.gemini_generate


async def test_execution_context_minimum(execution_graph_with_mock):
    """Proposal recebe apenas os campos necessários (ADR-002)."""
    graph, mock_proposal = execution_graph_with_mock
    await graph.ainvoke(_base_state())

    ctx = mock_proposal.run.call_args[0][0]
    assert "tender_schema" in ctx
    assert "pricing" in ctx
    assert "bid_decision" in ctx
    assert "human_approvals" in ctx
    assert "run_id" in ctx
    assert "tenant_id" in ctx
    assert "edital_pages" not in ctx
    assert "eligibility" not in ctx


async def test_execution_audit_log_model_used(execution_graph_with_mock):
    graph, _ = execution_graph_with_mock
    result = await graph.ainvoke(_base_state())

    assert result["audit_log"][0].model_used == settings.gemini_generate
