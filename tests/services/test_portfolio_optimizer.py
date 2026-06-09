"""Tests for portfolio_optimizer — AT-001..AT-006."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.schemas.portfolio import Oportunidade, PortfolioOtimizacaoInput
from src.services.portfolio_optimizer import _knapsack_greedy, _calcular_resultado, otimizar


def _op(run_id: str, valor: float, custo: float, prob: float, cap: float = 10.0) -> Oportunidade:
    return Oportunidade(
        run_id=run_id,
        valor_estimado_brl=Decimal(str(valor)),
        bid_no_bid_score=prob / 100,
        probabilidade_vitoria_pct=prob,
        custo_estimado_brl=Decimal(str(custo)),
        prazo_pagamento_dias=30,
        capacidade_necessaria_pct=cap,
    )


def _make_input(ops: list[Oportunidade], capital: float = 200_000) -> PortfolioOtimizacaoInput:
    return PortfolioOtimizacaoInput(
        oportunidades=ops,
        capital_giro_disponivel_brl=Decimal(str(capital)),
        capacidade_maxima_pct=100.0,
        capacidade_atual_pct=0.0,
        max_contratos_simultaneos=5,
    )


# AT-001: conservador seleciona ≤3 com prob≥60%
def test_conservador_max_3_and_prob_filter():
    ops = [
        _op("A", 100_000, 30_000, 65),
        _op("B", 80_000, 25_000, 70),
        _op("C", 90_000, 28_000, 62),
        _op("D", 60_000, 20_000, 45),  # prob < 60% — excluída no conservador
        _op("E", 50_000, 15_000, 30),  # prob < 60%
    ]
    result = otimizar(_make_input(ops))
    sel = result.conservador.oportunidades_selecionadas
    assert len(sel) <= 3
    for rid in sel:
        op = next(o for o in ops if o.run_id == rid)
        assert op.probabilidade_vitoria_pct >= 60


# AT-002: capital comprometido ≤ capital_max_pct × capital_disponível
def test_capital_constraint_respected():
    ops = [_op(str(i), 100_000, 60_000, 70) for i in range(10)]
    result = otimizar(_make_input(ops, capital=200_000))
    for cenario in [result.conservador, result.moderado, result.agressivo]:
        assert float(cenario.capital_comprometido_brl) <= 200_000 * 0.90


# AT-003: sem oportunidades com prob≥60% → conservador retorna lista vazia
def test_no_candidates_conservador():
    ops = [
        _op("A", 100_000, 50_000, 30),
        _op("B", 80_000, 40_000, 45),
    ]
    result = otimizar(_make_input(ops))
    assert result.conservador.oportunidades_selecionadas == []
    assert float(result.conservador.valor_esperado_ponderado_brl) == 0


# AT-004: roi_esperado_pct formula
def test_roi_formula():
    ops = [_op("X", 100_000, 40_000, 80)]
    result = _calcular_resultado("Moderado", ops)
    val_esperado = 100_000 * 0.80  # 80_000
    custo = 40_000
    expected_roi = (val_esperado - custo) / custo * 100  # 100%
    assert abs(result.roi_esperado_pct - expected_roi) < 0.01


# AT-005: capacidade_utilizada_pct = soma das capacidades selecionadas
def test_capacidade_utilizada():
    ops = [
        _op("A", 100_000, 30_000, 70, cap=15.0),
        _op("B", 80_000, 25_000, 75, cap=20.0),
    ]
    result = _calcular_resultado("Moderado", ops)
    assert result.capacidade_utilizada_pct == 35.0


# AT-006: oportunidades_rejeitadas = run_ids fora de todos os cenários
def test_rejeitadas_not_in_any_cenario():
    ops = [
        _op("GOOD", 200_000, 50_000, 80),
        _op("BAD",  50_000, 200_000, 10),  # custo > capital disponível, prob baixa
    ]
    result = otimizar(_make_input(ops, capital=100_000))
    all_sel = set(
        result.conservador.oportunidades_selecionadas
        + result.moderado.oportunidades_selecionadas
        + result.agressivo.oportunidades_selecionadas
    )
    for rid in result.oportunidades_rejeitadas:
        assert rid not in all_sel


# Greedy orders by efficiency
def test_greedy_selects_highest_efficiency_first():
    high_eff = _op("H", 100_000, 10_000, 80)   # efficiency = 8.0
    low_eff  = _op("L", 100_000, 50_000, 80)   # efficiency = 1.6
    result = _knapsack_greedy(
        [low_eff, high_eff],
        capital_max=15_000,
        capacidade_max=100,
        max_contratos=1,
    )
    assert len(result) == 1
    assert result[0].run_id == "H"
