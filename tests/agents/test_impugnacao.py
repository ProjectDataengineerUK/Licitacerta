"""Unit tests for ImpugnacaoAgent — no real LLM calls."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.impugnacao import ImpugnacaoAgent, _calc_cost_brl, _extract_usage
from src.schemas.results import ComplianceResult, ImpugnacaoAction, Issue
from src.schemas.tender import TenderSchema

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_issue(severity: str = "high", description: str = "Cláusula restritiva") -> Issue:
    return Issue(description=description, severity=severity)


def _make_compliance(issues: list[Issue]) -> ComplianceResult:
    mock = MagicMock(spec=ComplianceResult)
    mock.restrictive_clauses = issues
    return mock


def _make_tender(data_abertura: date | None = None) -> TenderSchema:
    return TenderSchema(
        objeto="Aquisição de equipamentos",
        orgao="Órgão Teste",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ ativo"],
        exigencias_tecnicas=[],
        penalidades=["Multa de 2%"],
        valor_estimado=Decimal("100000.00"),
        data_abertura=data_abertura,
    )


def _fake_raw() -> MagicMock:
    return MagicMock(response_metadata={"usage": {}})


def _llm_result(parsed: ImpugnacaoAction) -> dict:
    return {"parsed": parsed, "raw": _fake_raw(), "parsing_error": None}


def _make_action_result(tipo: str = "impugnar", valido: bool = True) -> ImpugnacaoAction:
    return ImpugnacaoAction(
        tipo=tipo,
        clause_description="Cláusula problemática",
        fundamento_legal="Art. 41, Lei 14.133/2021",
        minuta="Minuta de impugnação...",
        prazo_limite=date(2099, 12, 31) if valido else date(2000, 1, 1),
        valido=valido,
    )


# ── AT-001: no high/critical → participar, LLM NOT called ──────────────────

def test_at001_no_high_critical_returns_participar():
    agent = ImpugnacaoAgent.__new__(ImpugnacaoAgent)
    agent._llm = MagicMock()

    compliance = _make_compliance([_make_issue("low"), _make_issue("medium")])
    result = agent.run({"compliance_result": compliance, "tender_schema": _make_tender()})

    assert result.recommendation == "participar"
    assert result.actions == []
    agent._llm.invoke.assert_not_called()


def test_at001_no_issues_returns_participar():
    agent = ImpugnacaoAgent.__new__(ImpugnacaoAgent)
    agent._llm = MagicMock()

    compliance = _make_compliance([])
    result = agent.run({"compliance_result": compliance})

    assert result.recommendation == "participar"
    agent._llm.invoke.assert_not_called()


# ── AT-002: one "high" clause → pedir_esclarecimento ───────────────────────

def test_at002_one_high_clause_returns_pedir_esclarecimento():
    action = _make_action_result(tipo="pedir_esclarecimento")
    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = llm_mock
    llm_mock.invoke.return_value = _llm_result(action)

    with patch("src.agents.impugnacao.get_llm", return_value=llm_mock):
        agent = ImpugnacaoAgent()

    compliance = _make_compliance([_make_issue("high", "Certidão sem base legal")])
    with patch.object(agent, "_get_bq", return_value=None), \
         patch.object(agent, "_get_callbacks", return_value=[]):
        result = agent.run({"compliance_result": compliance, "tender_schema": _make_tender()})

    assert result.recommendation == "pedir_esclarecimento"
    assert len(result.actions) == 1
    assert result.human_decision_required is False


# ── AT-003: one "critical" clause → impugnar, HITL=True ───────────────────

def test_at003_one_critical_clause_returns_impugnar():
    action = _make_action_result(tipo="impugnar")
    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = llm_mock
    llm_mock.invoke.return_value = _llm_result(action)

    with patch("src.agents.impugnacao.get_llm", return_value=llm_mock):
        agent = ImpugnacaoAgent()

    compliance = _make_compliance([_make_issue("blocking", "Exigência ilegal de certidão privada")])
    with patch.object(agent, "_get_bq", return_value=None), \
         patch.object(agent, "_get_callbacks", return_value=[]):
        result = agent.run({"compliance_result": compliance, "tender_schema": _make_tender()})

    assert result.recommendation == "impugnar"
    assert result.human_decision_required is True


# ── AT-004: expired prazo → nao_participar ─────────────────────────────────

def test_at004_expired_prazo_returns_nao_participar():
    action = _make_action_result(tipo="impugnar", valido=False)
    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = llm_mock
    llm_mock.invoke.return_value = _llm_result(action)

    with patch("src.agents.impugnacao.get_llm", return_value=llm_mock):
        agent = ImpugnacaoAgent()

    compliance = _make_compliance([_make_issue("blocking")])
    tender = _make_tender(data_abertura=date(2000, 1, 5))  # far past → prazo expired
    with patch.object(agent, "_get_bq", return_value=None), \
         patch.object(agent, "_get_callbacks", return_value=[]):
        result = agent.run({"compliance_result": compliance, "tender_schema": tender})

    assert result.recommendation == "nao_participar"


# ── AT-005: mix high + critical → impugnar, 2 actions ─────────────────────

def test_at005_mix_high_critical_returns_impugnar_two_actions():
    action_high = _make_action_result(tipo="pedir_esclarecimento")
    action_critical = _make_action_result(tipo="impugnar")

    call_count = 0

    def _side_effect(messages, config=None):
        nonlocal call_count
        call_count += 1
        return _llm_result(action_high if call_count == 1 else action_critical)

    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = llm_mock
    llm_mock.invoke.side_effect = _side_effect

    with patch("src.agents.impugnacao.get_llm", return_value=llm_mock):
        agent = ImpugnacaoAgent()

    compliance = _make_compliance([
        _make_issue("high", "Exigência de marca"),
        _make_issue("blocking", "Certidão sem base legal"),
    ])
    with patch.object(agent, "_get_bq", return_value=None), \
         patch.object(agent, "_get_callbacks", return_value=[]):
        result = agent.run({"compliance_result": compliance, "tender_schema": _make_tender()})

    assert result.recommendation == "impugnar"
    assert len(result.actions) == 2


# ── AT-006: minuta has content (not empty) ────────────────────────────────

def test_at006_minuta_has_content():
    action = ImpugnacaoAction(
        tipo="impugnar",
        clause_description="Especificação de marca Dell",
        fundamento_legal="Art. 41, §1º, Lei 14.133/2021; Acórdão TCU 2.500/2015-Plenário",
        minuta=(
            "Senhor Pregoeiro,\n\n"
            "Vem à presença de Vossa Senhoria interpor IMPUGNAÇÃO ao Edital do Pregão Eletrônico "
            "n.º 001/2024, em razão da exigência de especificação de marca na cláusula 3.1.2, "
            "conforme vedação expressa do Art. 41, §1º da Lei 14.133/2021 e Acórdão TCU "
            "2.500/2015-Plenário.\n\n"
            "Ante o exposto, requer-se a anulação da referida cláusula.\n\n"
            "Respeitosamente."
        ),
        prazo_limite=date(2099, 12, 31),
        valido=True,
    )

    llm_mock = MagicMock()
    llm_mock.with_structured_output.return_value = llm_mock
    llm_mock.invoke.return_value = _llm_result(action)

    with patch("src.agents.impugnacao.get_llm", return_value=llm_mock):
        agent = ImpugnacaoAgent()

    compliance = _make_compliance([_make_issue("blocking")])
    with patch.object(agent, "_get_bq", return_value=None), \
         patch.object(agent, "_get_callbacks", return_value=[]):
        result = agent.run({"compliance_result": compliance, "tender_schema": _make_tender()})

    assert len(result.actions) == 1
    minuta = result.actions[0].minuta
    assert len(minuta) > 100
    assert "impugnação" in minuta.lower() or "impugnar" in minuta.lower() or "Impugnação" in minuta


# ── cost helpers ──────────────────────────────────────────────────────────

def test_calc_cost_brl_zero():
    assert _calc_cost_brl(0, 0) == 0.0


def test_calc_cost_brl_positive():
    cost = _calc_cost_brl(1_000_000, 0)
    assert cost == pytest.approx(3.0 * 5.0, rel=1e-3)


def test_extract_usage_empty_raw():
    raw = MagicMock(spec=[])
    assert _extract_usage(raw) == (0, 0)


# ── async ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_arun_no_high_critical_returns_participar():
    agent = ImpugnacaoAgent.__new__(ImpugnacaoAgent)
    agent._llm = AsyncMock()

    compliance = _make_compliance([])
    result = await agent.arun({"compliance_result": compliance})
    assert result.recommendation == "participar"
    agent._llm.ainvoke.assert_not_called()
