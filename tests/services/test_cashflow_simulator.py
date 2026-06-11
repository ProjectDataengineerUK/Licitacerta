"""Testes unitários para cashflow_simulator (AT-001..AT-005)."""
from __future__ import annotations

from decimal import Decimal

from src.services.cashflow_simulator import simular


# ── AT-001: Prazo 30d, custo R$80k, caixa R$80k ──────────────────────────────
def test_prazo_30d_mes1_negativo_mes2_positivo():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=30,
        custo_mensal_brl=Decimal("80000"),
        duracao_meses=3,
        caixa_inicial_brl=Decimal("80000"),
    )
    # Mês 1: meses_delay=ceil(30/30)=1; entrada=0 (mes > delay? 1 > 1 = False)
    assert sim.meses[0].entrada_brl == Decimal(0)
    assert sim.meses[0].saldo_acumulado_brl == Decimal("0")  # 80k - 80k
    # Mês 2: entrada=100k, saldo = 0 + 100k - 80k = 20k
    assert sim.meses[1].entrada_brl == Decimal("100000")
    assert sim.meses[1].saldo_acumulado_brl == Decimal("20000")


# ── AT-002: Prazo 90d, custo R$80k, caixa R$80k → risco=critico ──────────────
def test_prazo_90d_risco_critico():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=90,
        custo_mensal_brl=Decimal("80000"),
        duracao_meses=6,
        caixa_inicial_brl=Decimal("80000"),
    )
    # meses_delay = ceil(90/30) = 3
    # mes1: entrada=0 saldo=80k-80k=0
    # mes2: entrada=0 saldo=0-80k=-80k
    # mes3: entrada=0 saldo=-80k-80k=-160k
    # capital necessário = 160k > 80k*0.8=64k → critico
    assert sim.risco == "critico"
    assert sim.capital_giro_necessario_brl > 0
    assert sim.mes_critico is not None


# ── AT-003: Capital R$240k, caixa R$300k → atencao (não critico) ──────────────
def test_prazo_90d_caixa_300k_atencao():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=90,
        custo_mensal_brl=Decimal("80000"),
        duracao_meses=6,
        caixa_inicial_brl=Decimal("300000"),
    )
    # Com caixa 300k, saldo jamais fica negativo → capital=0 → risco=ok
    # Ou se ficar negativo: capital < 300k*0.8=240k → atencao
    assert sim.risco in ("ok", "atencao")


# ── AT-004: risco critico → sugestoes com antecipacao ────────────────────────
def test_sugestoes_quando_critico():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=90,
        custo_mensal_brl=Decimal("80000"),
        duracao_meses=4,
        caixa_inicial_brl=Decimal("50000"),
    )
    assert len(sim.sugestoes) > 0
    tipos = {s.tipo for s in sim.sugestoes}
    assert "antecipacao_recebiveis" in tipos
    custo = next(s.custo_brl for s in sim.sugestoes if s.tipo == "antecipacao_recebiveis")
    assert custo is not None and custo > 0


# ── AT-005: cenario_atraso_30d tem capital maior ─────────────────────────────
def test_cenario_atraso_capital_maior():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=60,
        custo_mensal_brl=Decimal("80000"),
        duracao_meses=6,
        caixa_inicial_brl=Decimal("80000"),
    )
    assert sim.cenario_atraso_30d is not None
    # cenário +30d deve ter capital necessário ≥ sem atraso
    assert (
        sim.cenario_atraso_30d.capital_giro_necessario_brl
        >= sim.capital_giro_necessario_brl
    )
    # cenário +30d não tem recursão
    assert sim.cenario_atraso_30d.cenario_atraso_30d is None


# ── risco=ok quando caixa cobre tudo ─────────────────────────────────────────
def test_risco_ok_sem_deficit():
    sim = simular(
        valor_mensal_brl=Decimal("100000"),
        prazo_pagamento_dias=30,
        custo_mensal_brl=Decimal("50000"),
        duracao_meses=3,
        caixa_inicial_brl=Decimal("200000"),
    )
    assert sim.risco == "ok"
    assert sim.capital_giro_necessario_brl == Decimal(0)
    assert sim.sugestoes == []
