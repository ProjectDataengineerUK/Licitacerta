from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.graph.state import initial_state
from src.schemas.results import (
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    LegalRegimeResult,
)
from src.schemas.tender import Evidence, TenderSchema


def _make_tender_schema() -> TenderSchema:
    return TenderSchema(
        objeto="Fornecimento de papel",
        orgao="Secretaria de Educação",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ", "CND Federal"],
        exigencias_tecnicas=[],
        penalidades=["Multa de 5%"],
        evidence=[],
    )


def _make_eligibility(eligible: bool = True) -> EligibilityResult:
    return EligibilityResult(
        conclusion="Empresa elegível para participar.",
        confidence=0.9,
        is_eligible=eligible,
        recommended_action="Participar",
    )


def _make_compliance(risk: str = "low") -> ComplianceResult:
    return ComplianceResult(
        conclusion="Sem cláusulas restritivas relevantes.",
        confidence=0.85,
        risk_level=risk,
        recommended_action="Participar normalmente",
    )


def _make_blacklist(blocked: bool = False) -> BlacklistResult:
    return BlacklistResult(
        ceis_blocked=blocked,
        cnep_blocked=False,
        cepim_blocked=False,
        any_blocked=blocked,
        checked_at=datetime.utcnow(),
    )


@pytest.fixture()
def validation_graph_with_mocks():
    mock_elig = MagicMock()
    mock_elig.run.return_value = _make_eligibility()
    mock_comp = MagicMock()
    mock_comp.run.return_value = _make_compliance()
    mock_blacklist_fn = MagicMock(return_value=_make_blacklist())

    with (
        patch("src.graph.subgraphs.validation.EligibilityAgent", return_value=mock_elig),
        patch("src.graph.subgraphs.validation.ComplianceAgent", return_value=mock_comp),
    ):
        from src.graph.subgraphs.validation import build_validation_subgraph
        graph = build_validation_subgraph(blacklist_fn=mock_blacklist_fn)
    return graph, mock_elig, mock_comp, mock_blacklist_fn


def _base_state():
    state = initial_state("edital-001", "texto", "12345678000195")
    state["tender_schema"] = _make_tender_schema()
    state["legal_regime"] = LegalRegimeResult(
        primary_law="lei_14133", modality="pregao_eletronico", confidence=0.9
    )
    return state


def test_validation_happy_path(validation_graph_with_mocks):
    graph, _, _, _ = validation_graph_with_mocks
    result = graph.invoke(_base_state())

    assert result["current_step"] == "validated"
    assert result["eligibility"].is_eligible is True
    assert result["compliance"].risk_level == "low"
    assert result["blacklist"].any_blocked is False
    assert len(result["audit_log"]) == 3
    assert result["errors"] == []


def test_validation_blacklist_blocked(validation_graph_with_mocks):
    graph, _, _, mock_bl = validation_graph_with_mocks
    mock_bl.return_value = _make_blacklist(blocked=True)

    result = graph.invoke(_base_state())

    assert result["current_step"] == "validated"
    assert result["blacklist"].any_blocked is True
    assert result["blacklist"].ceis_blocked is True


def test_validation_eligibility_error_continues(validation_graph_with_mocks):
    graph, mock_elig, _, _ = validation_graph_with_mocks
    mock_elig.run.side_effect = RuntimeError("timeout da API")

    result = graph.invoke(_base_state())

    assert result["current_step"] == "validated"
    assert any(e.agent == "eligibility" for e in result["errors"])
    # Compliance e blacklist continuam mesmo com erro de eligibility
    assert result["compliance"] is not None
    assert result["blacklist"] is not None


def test_validation_audit_log_has_deterministic_blacklist(validation_graph_with_mocks):
    graph, _, _, _ = validation_graph_with_mocks
    result = graph.invoke(_base_state())

    bl_events = [e for e in result["audit_log"] if e.agent == "blacklist"]
    assert len(bl_events) == 1
    assert bl_events[0].model_used == "deterministic"


def test_validation_context_minimum(validation_graph_with_mocks):
    """Verifica que eligibility recebe apenas tender_schema + company_cnpj (ADR-002)."""
    graph, mock_elig, _, _ = validation_graph_with_mocks
    result = graph.invoke(_base_state())

    call_context = mock_elig.run.call_args[0][0]
    assert "tender_schema" in call_context
    assert "company_cnpj" in call_context
    assert "edital_pages" not in call_context
