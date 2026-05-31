"""PRECIFICACAO_AVANCADA — tributário, BDI, capital de giro, cenários."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.services.bdi import calcular_bdi_obras
from src.services.precificacao import estimar_capital_giro, gerar_cenarios
from src.services.tributario import calcular_impostos


# --------------------------------------------------------------------------- #
# Tributário
# --------------------------------------------------------------------------- #
def test_at001_simples_servicos():
    r = calcular_impostos(Decimal("50000"), "simples", "servicos", faturamento_anual=Decimal("360000"))
    assert r.aliquota_total_pct == pytest.approx(11.2)
    assert r.valor_impostos_brl == Decimal("5600.00")


def test_at002_lucro_presumido_servicos():
    r = calcular_impostos(Decimal("50000"), "lucro_presumido", "servicos")
    assert r.aliquota_total_pct == pytest.approx(16.33, abs=1e-2)
    assert r.valor_impostos_brl == Decimal("8165.00")
    assert "iss" in r.detalhamento


def test_simples_faixa_inicial():
    r = calcular_impostos(Decimal("10000"), "simples", faturamento_anual=Decimal("100000"))
    assert r.aliquota_total_pct == pytest.approx(6.0)


def test_lucro_real_orienta_contador():
    with pytest.raises(ValueError, match="contador"):
        calcular_impostos(Decimal("50000"), "lucro_real")


# --------------------------------------------------------------------------- #
# AT-003 — BDI obras
# --------------------------------------------------------------------------- #
def test_at003_bdi_dentro_da_faixa_tcu():
    r = calcular_bdi_obras()
    assert 22.0 <= r.bdi_pct <= 28.0
    assert "lucro" in r.composicao
    assert "administracao_central" in r.composicao


def test_bdi_calcula_valor_quando_custo_informado():
    r = calcular_bdi_obras(custo_direto_brl=Decimal("100000"))
    assert r.valor_bdi_brl is not None
    assert r.valor_bdi_brl > 0


# --------------------------------------------------------------------------- #
# AT-004 / AT-005 — capital de giro
# --------------------------------------------------------------------------- #
def test_at004_capital_giro_warning():
    r = estimar_capital_giro(Decimal("80000"), prazo_pagamento_dias=60, limite_credito_brl=Decimal("100000"))
    assert r.capital_necessario_brl == Decimal("160000.00")
    assert r.alerta == "warning"


def test_at005_capital_giro_critical():
    r = estimar_capital_giro(Decimal("80000"), prazo_pagamento_dias=90, limite_credito_brl=Decimal("100000"))
    assert r.capital_necessario_brl == Decimal("240000.00")
    assert r.alerta == "critical"


def test_capital_giro_sem_limite_fica_ok():
    r = estimar_capital_giro(Decimal("80000"), prazo_pagamento_dias=90)
    assert r.alerta == "ok"


# --------------------------------------------------------------------------- #
# AT-006 — cenários
# --------------------------------------------------------------------------- #
def test_at006_cenarios_completos():
    cenarios = gerar_cenarios(
        custos_diretos_brl=Decimal("40000"),
        preco_base_brl=Decimal("50000"),
        regime="simples",
        prazo_pagamento_dias=60,
        faturamento_anual=Decimal("360000"),
    )
    assert len(cenarios) == 5
    by_nome = {c.nome: c for c in cenarios}
    assert by_nome["Base"].margem_liquida_brl > 0
    assert by_nome["Base"].viavel is True
    assert by_nome["Conservador -10%"].margem_liquida_brl < 0
    assert by_nome["Conservador -10%"].viavel is False
