"""Testes unitários para EstrategiaAgent (AT-001..AT-006)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.schemas.estrategia import AcaoEstrategica, EstrategiaResult
from src.schemas.results import BidDecision, ComplianceResult


def _make_bid() -> BidDecision:
    return BidDecision(
        conclusion="Participar com ressalvas",
        confidence=0.55,
        recommended_action="Participar",
        recommendation="participar_com_ressalvas",
        risk_level="medium",
        expected_margin_pct=12.0,
    )


def _make_compliance() -> ComplianceResult:
    return ComplianceResult(
        conclusion="Risco médio",
        confidence=0.80,
        recommended_action="Verificar cláusulas",
        risk_level="medium",
    )


def _mock_llm(result: EstrategiaResult):
    mock = MagicMock()
    inner = MagicMock()
    inner.ainvoke = AsyncMock(return_value={"parsed": result, "raw": MagicMock(response_metadata={"usage": {}})})
    mock.with_structured_output.return_value = inner
    return mock


def _sample_result(prob_sem=55.0, prob_com=75.0, n_acoes=5) -> EstrategiaResult:
    acoes = [
        AcaoEstrategica(
            numero=i,
            categoria="documentacao",
            titulo=f"Ação {i}",
            descricao="Descrição",
            prazo="3 dias",
            impacto_vitoria_pct=4.0,
        )
        for i in range(1, n_acoes + 1)
    ]
    return EstrategiaResult(
        probabilidade_sem_acoes_pct=prob_sem,
        probabilidade_com_acoes_pct=prob_com,
        acoes=acoes,
        resumo_executivo="Estratégia competitiva elaborada.",
    )


# ── AT-001: run completo → 5 ações geradas ───────────────────────────────────
def test_run_completo_5_acoes():
    async def _run():
        with patch("src.agents.estrategia.get_llm", return_value=_mock_llm(_sample_result())):
            from src.agents.estrategia import EstrategiaAgent
            agent = EstrategiaAgent()
            return await agent.arun({
                "bid_decision": _make_bid(),
                "compliance": _make_compliance(),
                "run_id": "at-001",
            })

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert len(result.acoes) == 5
    assert result.probabilidade_com_acoes_pct > result.probabilidade_sem_acoes_pct


# ── AT-002: soma impacto_pct ≤ 40 ────────────────────────────────────────────
def test_soma_impacto_pct():
    r = _sample_result()
    total = sum(a.impacto_vitoria_pct for a in r.acoes)
    assert total <= 40.0


# ── AT-005: sem bid_decision → data_insuficiente=True ────────────────────────
def test_sem_bid_decision_data_insuficiente():
    async def _run():
        from src.agents.estrategia import EstrategiaAgent
        with patch("src.agents.estrategia.get_llm", return_value=MagicMock()):
            agent = EstrategiaAgent()
        return await agent.arun({
            "bid_decision": None,
            "compliance": _make_compliance(),
            "run_id": "at-005",
        })

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.data_insuficiente is True
    assert result.acoes == []


# ── AT-006: prob_com_acoes clamped a 95% ─────────────────────────────────────
def test_probabilidade_clamped_95():
    high_result = _sample_result(prob_sem=80.0, prob_com=120.0)  # LLM returned >95
    async def _run():
        with patch("src.agents.estrategia.get_llm", return_value=_mock_llm(high_result)):
            from src.agents.estrategia import EstrategiaAgent
            agent = EstrategiaAgent()
            return await agent.arun({
                "bid_decision": _make_bid(),
                "compliance": _make_compliance(),
                "run_id": "at-006",
            })

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.probabilidade_com_acoes_pct <= 95.0


# ── AT-002 b: max 5 ações mesmo se LLM retorna 7 ─────────────────────────────
def test_max_5_acoes():
    over_result = _sample_result(n_acoes=7)
    async def _run():
        with patch("src.agents.estrategia.get_llm", return_value=_mock_llm(over_result)):
            from src.agents.estrategia import EstrategiaAgent
            agent = EstrategiaAgent()
            return await agent.arun({
                "bid_decision": _make_bid(),
                "compliance": _make_compliance(),
                "run_id": "at-002b",
            })

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert len(result.acoes) <= 5
