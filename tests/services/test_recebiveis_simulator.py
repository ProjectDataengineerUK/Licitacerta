"""Tests for recebiveis_simulator — AT-001..AT-003."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.services.recebiveis_simulator import simular, TAXA_MENSAL_PADRAO


# AT-001: simular(R$50k, 60d) → custo = 50000 × 0.015 × 2 = R$1.500; liquido = R$48.500
def test_simular_basico():
    result = simular(Decimal("50000"), 60)
    assert result.elegivel is True
    assert result.custo_antecipacao_brl == Decimal("1500.00")
    assert result.valor_liquido_brl == Decimal("48500.00")
    assert result.taxa_mensal_pct == 1.5
    assert abs(result.taxa_periodo - 1.5 * 2 / 100) < 0.0001


# AT-002: valor < R$5k → elegivel=False
def test_valor_abaixo_minimo():
    result = simular(Decimal("4000"), 60)
    assert result.elegivel is False
    assert result.motivo_inelegivel is not None
    assert "5" in result.motivo_inelegivel
    assert result.custo_antecipacao_brl == Decimal(0)
    assert result.valor_liquido_brl == Decimal("4000")


# AT-003: prazo < 30d → elegivel=False
def test_prazo_abaixo_minimo():
    result = simular(Decimal("50000"), 15)
    assert result.elegivel is False
    assert result.motivo_inelegivel is not None
    assert "30" in result.motivo_inelegivel


# Taxa customizada
def test_taxa_customizada():
    result = simular(Decimal("10000"), 30, taxa_mensal_pct=2.0)
    assert result.taxa_mensal_pct == 2.0
    # custo = 10000 × 0.02 × (30/30) = 200
    assert result.custo_antecipacao_brl == Decimal("200.00")
    assert result.valor_liquido_brl == Decimal("9800.00")


# CEA está preenchido para elegíveis
def test_cea_preenchido():
    result = simular(Decimal("20000"), 60)
    assert result.custo_efetivo_anual_pct > 0


# Prazo exatamente no limite
def test_prazo_exato_minimo():
    result = simular(Decimal("10000"), 30)
    assert result.elegivel is True
