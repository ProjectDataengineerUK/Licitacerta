"""Compliance agent evals — 5 fixture cases, LLM mocked for CI cost.

Set EVAL_REAL=true to run 1 case against a live LLM.
Pass threshold: >=80% of assertions must pass (enforced by eval-gate.yml).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from src.schemas.results import ComplianceResult
from src.schemas.tender import TenderSchema


def _make_tender(**kwargs) -> TenderSchema:
    defaults = dict(
        numero="001/2024",
        objeto="Aquisição de material de escritório",
        modalidade="pregao_eletronico",
        tipo_objeto="produto",
        valor_estimado=None,
        criterio_julgamento="menor_preco",
        orgao="Prefeitura Municipal",
        uasg="123456",
    )
    defaults.update(kwargs)
    return TenderSchema(**defaults)


def _mock_llm_response(risk_level: str = "low", human_required: bool = False) -> Any:
    result = ComplianceResult(
        conclusion="Análise mock",
        confidence=0.85,
        recommended_action="Participar",
        risk_level=risk_level,
        human_decision_required=human_required,
    )
    payload = {"parsed": result, "raw": MagicMock(response_metadata={"usage": {}})}
    structured = MagicMock()
    structured.invoke.return_value = payload
    structured.ainvoke = structured.invoke
    mock = MagicMock()
    mock.with_structured_output.return_value = structured
    mock.invoke.return_value = payload
    mock.ainvoke = mock.invoke
    return mock


# ── Eval-001: Edital limpo → low risk ────────────────────────────────────────
def test_eval_edital_limpo_low_risk():
    tender = _make_tender(objeto="Fornecimento de papel A4")
    with patch("src.agents.compliance.get_llm", return_value=_mock_llm_response("low")):
        from src.agents.compliance import ComplianceAgent
        agent = ComplianceAgent()
        result = agent.run({"tender_schema": tender, "run_id": "eval-001"})
    assert result.risk_level in ("low", "medium")
    assert result.human_decision_required is False


# ── Eval-002: Exigência de marca → high risk ─────────────────────────────────
def test_eval_especificacao_marca_high_risk():
    tender = _make_tender(
        objeto="Notebook Dell Inspiron 15 i7",
        exigencias_tecnicas=["Apenas marca Dell aceita"],
    )
    with patch("src.agents.compliance.get_llm", return_value=_mock_llm_response("high", human_required=True)):
        from src.agents.compliance import ComplianceAgent
        agent = ComplianceAgent()
        result = agent.run({"tender_schema": tender, "run_id": "eval-002"})
    assert result.risk_level in ("high", "critical")
    assert result.human_decision_required is True


# ── Eval-003: Garantia >10% → high risk ──────────────────────────────────────
def test_eval_garantia_desproporcional():
    tender = _make_tender(
        objeto="Obra de construção",
        garantia_percentual=15.0,
    )
    with patch("src.agents.compliance.get_llm", return_value=_mock_llm_response("high", human_required=True)):
        from src.agents.compliance import ComplianceAgent
        agent = ComplianceAgent()
        result = agent.run({"tender_schema": tender, "run_id": "eval-003"})
    assert result.risk_level in ("high", "critical")


# ── Eval-004: Tipo serviço → supply_chain ignorado ───────────────────────────
def test_eval_servico_sem_supply_chain():
    tender = _make_tender(tipo_objeto="servico", objeto="Limpeza predial")
    with patch("src.agents.compliance.get_llm", return_value=_mock_llm_response("low")):
        from src.agents.compliance import ComplianceAgent
        agent = ComplianceAgent()
        result = agent.run({"tender_schema": tender, "run_id": "eval-004"})
    assert result.supply_chain is None


# ── Eval-005: Critério subjetivo → medium/high ───────────────────────────────
def test_eval_criterio_subjetivo():
    tender = _make_tender(
        objeto="Assessoria técnica especializada",
        criterio_julgamento="melhor_tecnica",
    )
    with patch("src.agents.compliance.get_llm", return_value=_mock_llm_response("medium")):
        from src.agents.compliance import ComplianceAgent
        agent = ComplianceAgent()
        result = agent.run({"tender_schema": tender, "run_id": "eval-005"})
    assert result.risk_level in ("medium", "high", "critical")
