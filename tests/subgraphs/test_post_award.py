from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.agents.contract import ContractObligation, ContractResult
from src.config import settings
from src.graph.state import initial_state
from src.schemas.results import ProposalDraft
from src.schemas.tender import TenderSchema


def _make_contract_result() -> ContractResult:
    return ContractResult(
        contract_status="active",
        obligations=[
            ContractObligation(
                description="Entrega dos materiais",
                due_date="2026-06-22",
                recurrent=False,
                status="pending",
            ),
            ContractObligation(
                description="Nota Fiscal para pagamento",
                due_date="2026-06-25",
                recurrent=True,
                status="pending",
            ),
        ],
        next_payment_date="2026-07-25",
        reajuste_due=False,
        reajuste_index=None,
        warnings=["Prazo de entrega em 30 dias — preparar logística"],
        human_decision_required=False,
        recommended_action="Iniciar preparação da entrega",
    )


def _base_state():
    state = initial_state("edital-pa-001", "texto", "12345678000195")
    state["current_step"] = "executed"
    state["tender_schema"] = TenderSchema(
        objeto="Fornecimento de papel A4",
        orgao="Câmara Municipal",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=[],
        exigencias_tecnicas=[],
        penalidades=[],
        evidence=[],
    )
    state["proposal_draft"] = ProposalDraft(
        content="Proposta aprovada",
        price=Decimal("47058.82"),
        validity_days=60,
        generated_at=datetime.utcnow(),
        approved_by="jonatas",
    )
    return state


@pytest.fixture()
def post_award_graph_with_mock():
    mock_contract = MagicMock()
    mock_contract.run.return_value = _make_contract_result()

    with patch("src.graph.subgraphs.post_award.ContractAgent", return_value=mock_contract):
        from src.graph.subgraphs.post_award import build_post_award_subgraph
        graph = build_post_award_subgraph()
        yield graph, mock_contract


async def test_post_award_happy_path(post_award_graph_with_mock):
    graph, _ = post_award_graph_with_mock
    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "completed"
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].subgraph == "post_award"
    assert result["errors"] == []


async def test_post_award_error_still_completes(post_award_graph_with_mock):
    graph, mock_contract = post_award_graph_with_mock
    mock_contract.run.side_effect = RuntimeError("API indisponível")

    result = await graph.ainvoke(_base_state())

    assert result["current_step"] == "completed"
    assert len(result["errors"]) == 1
    assert result["errors"][0].recoverable is True


async def test_post_award_audit_summary(post_award_graph_with_mock):
    graph, _ = post_award_graph_with_mock
    result = await graph.ainvoke(_base_state())

    summary = result["audit_log"][0].output_summary
    assert "active" in summary
    assert "obligations=2" in summary


async def test_post_award_audit_log_model_used(post_award_graph_with_mock):
    graph, _ = post_award_graph_with_mock
    result = await graph.ainvoke(_base_state())

    assert result["audit_log"][0].model_used == settings.gemini_pro
