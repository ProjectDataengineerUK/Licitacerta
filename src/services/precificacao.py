"""PRECIFICACAO_AVANCADA — capital de giro e simulação de cenários."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.schemas.results import CapitalGiroResult, CenarioPrecificacao
from src.services.tributario import calcular_impostos

_CENT = Decimal("0.01")

# Ajustes de preço por cenário (ATs: Base positiva, Conservador provavelmente negativa)
_CENARIOS = [
    ("Conservador -10%", Decimal("-0.10")),
    ("Moderado -5%", Decimal("-0.05")),
    ("Base", Decimal("0.00")),
    ("Agressivo +5%", Decimal("0.05")),
    ("Otimista +10%", Decimal("0.10")),
]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def estimar_capital_giro(
    custos_diretos_brl: Decimal,
    prazo_pagamento_dias: int,
    ciclo_operacional_dias: int = 30,
    limite_credito_brl: Decimal | None = None,
) -> CapitalGiroResult:
    """capital_necessario = custos_diretos × (prazo_pagamento / ciclo_operacional).

    Alerta (calibrado pelos AT): warning quando excede ~80% do crédito disponível,
    critical quando excede 2× o limite.
    """
    fator = Decimal(prazo_pagamento_dias) / Decimal(ciclo_operacional_dias or 30)
    capital = _q(custos_diretos_brl * fator)

    alerta = "ok"
    if limite_credito_brl and limite_credito_brl > 0:
        ratio = capital / limite_credito_brl
        if ratio >= Decimal("2.0"):
            alerta = "critical"
        elif ratio >= Decimal("0.8"):
            alerta = "warning"
    return CapitalGiroResult(
        capital_necessario_brl=capital,
        alerta=alerta,
        limite_credito_brl=limite_credito_brl,
    )


def _custo_financeiro(valor: Decimal, prazo_dias: int, selic_anual_pct: float) -> Decimal:
    selic = Decimal(str(selic_anual_pct)) / 100
    return _q(valor * selic / Decimal("360") * Decimal(prazo_dias))


def gerar_cenarios(
    *,
    custos_diretos_brl: Decimal,
    preco_base_brl: Decimal,
    regime: str,
    segmento: str = "servicos",
    prazo_pagamento_dias: int = 0,
    faturamento_anual: Decimal | None = None,
    selic_anual_pct: float = 11.75,
    ciclo_operacional_dias: int = 30,
) -> list[CenarioPrecificacao]:
    """Tabela de cenários (-10% a +10%) com margem líquida após impostos e custo financeiro."""
    cenarios: list[CenarioPrecificacao] = []
    capital = (custos_diretos_brl * Decimal(prazo_pagamento_dias)
               / Decimal(ciclo_operacional_dias or 30))
    capital = _q(capital)

    for nome, ajuste in _CENARIOS:
        valor = _q(preco_base_brl * (Decimal("1") + ajuste))
        impostos = calcular_impostos(valor, regime, segmento, faturamento_anual).valor_impostos_brl
        custo_fin = _custo_financeiro(valor, prazo_pagamento_dias, selic_anual_pct)
        margem_liq = _q(valor - custos_diretos_brl - impostos - custo_fin)
        margem_bruta_pct = float(((valor - custos_diretos_brl) / valor * 100)) if valor else 0.0
        margem_liq_pct = float((margem_liq / valor * 100)) if valor else 0.0
        cenarios.append(CenarioPrecificacao(
            nome=nome,
            valor_proposta_brl=valor,
            margem_bruta_pct=round(margem_bruta_pct, 2),
            margem_liquida_pct=round(margem_liq_pct, 2),
            margem_liquida_brl=margem_liq,
            capital_necessario_brl=capital,
            viavel=margem_liq > 0,
        ))
    return cenarios
