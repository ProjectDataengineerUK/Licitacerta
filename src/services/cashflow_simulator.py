from __future__ import annotations

from decimal import Decimal
from math import ceil

from src.schemas.cashflow import CashflowSimulation, MesCashflow, SugestaoMitigacao


def simular(
    valor_mensal_brl: Decimal,
    prazo_pagamento_dias: int,
    custo_mensal_brl: Decimal,
    duracao_meses: int,
    caixa_inicial_brl: Decimal,
    *,
    _calc_atraso: bool = True,
) -> CashflowSimulation:
    meses_delay = ceil(prazo_pagamento_dias / 30)
    meses: list[MesCashflow] = []
    saldo = caixa_inicial_brl

    for mes in range(1, duracao_meses + 1):
        entrada = valor_mensal_brl if mes > meses_delay else Decimal(0)
        saida = custo_mensal_brl
        saldo += entrada - saida
        meses.append(
            MesCashflow(
                mes=mes,
                entrada_brl=entrada,
                saida_brl=saida,
                saldo_acumulado_brl=saldo,
                positivo=saldo >= 0,
            )
        )

    saldo_minimo = min(m.saldo_acumulado_brl for m in meses)
    capital_necessario = max(Decimal(0), -saldo_minimo)
    mes_critico = next((m.mes for m in meses if not m.positivo), None)

    risco = _avaliar_risco(capital_necessario, caixa_inicial_brl)
    sugestoes = _gerar_sugestoes(capital_necessario, valor_mensal_brl, prazo_pagamento_dias)

    cenario_atraso: CashflowSimulation | None = None
    if _calc_atraso:
        cenario_atraso = simular(
            valor_mensal_brl,
            prazo_pagamento_dias + 30,
            custo_mensal_brl,
            duracao_meses,
            caixa_inicial_brl,
            _calc_atraso=False,
        )

    return CashflowSimulation(
        valor_mensal_brl=valor_mensal_brl,
        custo_mensal_brl=custo_mensal_brl,
        prazo_pagamento_dias=prazo_pagamento_dias,
        duracao_meses=duracao_meses,
        caixa_inicial_brl=caixa_inicial_brl,
        meses=meses,
        saldo_minimo_brl=saldo_minimo,
        capital_giro_necessario_brl=capital_necessario,
        risco=risco,
        mes_critico=mes_critico,
        sugestoes=sugestoes,
        cenario_atraso_30d=cenario_atraso,
    )


def _avaliar_risco(
    capital_necessario: Decimal, caixa_inicial: Decimal
) -> str:
    if capital_necessario == 0:
        return "ok"
    if caixa_inicial > 0 and capital_necessario > caixa_inicial * Decimal("0.8"):
        return "critico"
    return "atencao"


def _gerar_sugestoes(
    capital_necessario: Decimal,
    valor_mensal: Decimal,
    prazo_dias: int,
) -> list[SugestaoMitigacao]:
    if capital_necessario == 0:
        return []

    taxa_antecipacao = Decimal("0.015")
    meses_decimal = Decimal(prazo_dias) / 30
    custo = valor_mensal * taxa_antecipacao * meses_decimal

    pct_empenho = int(capital_necessario / valor_mensal * 100) if valor_mensal else 0
    return [
        SugestaoMitigacao(
            tipo="antecipacao_recebiveis",
            descricao=f"Antecipar {pct_empenho}% do primeiro empenho",
            impacto_brl=capital_necessario,
            custo_brl=custo,
        ),
        SugestaoMitigacao(
            tipo="adiantamento_contratual",
            descricao="Negociar adiantamento de 20% na assinatura do contrato",
            impacto_brl=valor_mensal * Decimal("0.2"),
            custo_brl=Decimal(0),
        ),
    ]
