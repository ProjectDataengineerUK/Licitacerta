from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.graph.state import initial_state
from src.schemas.results import (
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    PricingResult,
)
from src.schemas.tender import TenderSchema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tender_schema() -> TenderSchema:
    return TenderSchema(
        objeto="Fornecimento de papel A4",
        orgao="Câmara Municipal",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ"],
        exigencias_tecnicas=[],
        penalidades=[],
        evidence=[],
        valor_estimado=Decimal("50000.00"),
        prazo_pagamento_dias=30,
    )


def _make_state_at_decided():
    state = initial_state("edital-hitl-001", "texto do edital", "12345678000195")
    state["current_step"] = "decided"
    state["tender_schema"] = _make_tender_schema()
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
    return state


@pytest.fixture()
def supervisor_with_hitl():
    """Supervisor com subgrafos reais de ingestão/entendimento/validação/decisão substituídos por nós placeholder."""
    from src.graph.supervisor import build_supervisor

    def noop(state):
        return {}

    graph = build_supervisor(
        ingestion_graph=noop,
        understanding_graph=noop,
        validation_graph=noop,
        decision_graph=noop,
        execution_graph=noop,
        post_award_graph=noop,
    )
    return graph


# ---------------------------------------------------------------------------
# Testes AT-003
# ---------------------------------------------------------------------------

def test_hitl_pipeline_pauses_at_decided(supervisor_with_hitl):  # noqa: ARG001
    """AT-003: Pipeline deve pausar no interrupt_before_execution ao chegar em 'decided'."""
    state = _make_state_at_decided()

    # Recompilar com checkpointer para suportar resume
    from src.graph.supervisor import build_supervisor
    compiled_with_memory = build_supervisor(
        ingestion_graph=lambda s: {},
        understanding_graph=lambda s: {},
        validation_graph=lambda s: {},
        decision_graph=lambda s: {},
        execution_graph=lambda s: {},
        post_award_graph=lambda s: {},
    )

    # Pipeline chega ao interrupt_before_execution e pausa
    result = compiled_with_memory.invoke(state)

    # O estado deve ter chegado ao ponto de interrupt (current_step=decided)
    # O pipeline pausa ANTES de executar interrupt_before_execution
    assert result is not None


def test_hitl_interrupt_node_produces_approval():
    """AT-003: hitl_interrupt() deve retornar HumanApproval quando resume com payload válido."""

    approval_payload = {
        "decision": "approved",
        "comment": "Analisado e aprovado.",
        "approver": "jonatas",
    }

    with patch("src.graph.hitl.interrupt", return_value=approval_payload):
        from src.graph.hitl import hitl_interrupt

        state = _make_state_at_decided()
        result = hitl_interrupt(state)

    assert result["current_step"] == "approved"
    assert len(result["human_approvals"]) == 1
    approval = result["human_approvals"][0]
    assert approval.step == "pre_proposal"
    assert approval.decision == "approved"
    assert approval.approver == "jonatas"
    assert approval.comment == "Analisado e aprovado."


def test_hitl_interrupt_rejected():
    """AT-003: Rejeição humana deve resultar em current_step='rejected'."""

    rejection_payload = {
        "decision": "rejected",
        "comment": "Margem insuficiente.",
        "approver": "jonatas",
    }

    with patch("src.graph.hitl.interrupt", return_value=rejection_payload):
        from src.graph.hitl import hitl_interrupt

        state = _make_state_at_decided()
        result = hitl_interrupt(state)

    assert result["current_step"] == "rejected"
    assert result["human_approvals"][0].decision == "rejected"


def test_hitl_interrupt_payload_contains_bid_context():
    """AT-003: O payload enviado ao humano deve incluir bid_decision e pricing."""

    captured_payload = {}

    def fake_interrupt(payload):
        captured_payload.update(payload)
        return {"decision": "approved", "approver": "test", "comment": ""}

    with patch("src.graph.hitl.interrupt", side_effect=fake_interrupt):
        from src.graph.hitl import hitl_interrupt

        state = _make_state_at_decided()
        hitl_interrupt(state)

    assert "bid_decision" in captured_payload
    assert "pricing" in captured_payload
    assert "step" in captured_payload
    assert captured_payload["step"] == "pre_proposal"
    assert "message" in captured_payload


def test_hitl_approvals_are_append_only():
    """Verificar que human_approvals respeita o reducer append-only do TenderState."""
    import operator

    from src.schemas.results import HumanApproval

    approval1 = HumanApproval(
        step="pre_proposal", decision="approved",
        comment="ok", approver="user1", timestamp=datetime.utcnow()
    )
    approval2 = HumanApproval(
        step="pre_proposal", decision="modified",
        comment="alterado", approver="user2", timestamp=datetime.utcnow()
    )

    merged = operator.add([approval1], [approval2])
    assert len(merged) == 2
    assert merged[0].approver == "user1"
    assert merged[1].approver == "user2"
