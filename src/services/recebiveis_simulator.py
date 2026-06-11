"""Recebiveis antecipacao simulator — deterministic local MVP (no fintech API)."""
from __future__ import annotations

from decimal import Decimal

from src.schemas.recebiveis import SimulacaoAntecipacao

TAXA_MENSAL_PADRAO = Decimal("0.015")  # 1,5%/mês
VALOR_MINIMO_BRL = Decimal("5000")
PRAZO_MINIMO_DIAS = 30


def simular(
    valor_bruto_brl: Decimal,
    prazo_dias: int,
    taxa_mensal_pct: float | None = None,
) -> SimulacaoAntecipacao:
    taxa = Decimal(str(taxa_mensal_pct / 100)) if taxa_mensal_pct is not None else TAXA_MENSAL_PADRAO
    elegivel, motivo = _check_elegibilidade(valor_bruto_brl, prazo_dias)

    if not elegivel:
        return SimulacaoAntecipacao(
            valor_bruto_brl=valor_bruto_brl,
            prazo_dias=prazo_dias,
            taxa_mensal_pct=float(taxa * 100),
            taxa_periodo=0.0,
            custo_antecipacao_brl=Decimal(0),
            valor_liquido_brl=valor_bruto_brl,
            custo_efetivo_anual_pct=0.0,
            elegivel=False,
            motivo_inelegivel=motivo,
        )

    taxa_periodo = taxa * (Decimal(str(prazo_dias)) / Decimal("30"))
    custo = (valor_bruto_brl * taxa_periodo).quantize(Decimal("0.01"))
    liquido = valor_bruto_brl - custo
    cea = ((1 + float(taxa)) ** 12 - 1) * 100

    return SimulacaoAntecipacao(
        valor_bruto_brl=valor_bruto_brl,
        prazo_dias=prazo_dias,
        taxa_mensal_pct=float(taxa * 100),
        taxa_periodo=float(taxa_periodo),
        custo_antecipacao_brl=custo,
        valor_liquido_brl=liquido,
        custo_efetivo_anual_pct=cea,
        elegivel=True,
    )


def _check_elegibilidade(valor: Decimal, prazo: int) -> tuple[bool, str | None]:
    if valor < VALOR_MINIMO_BRL:
        return False, f"Valor mínimo R$ {float(VALOR_MINIMO_BRL):,.0f}"
    if prazo < PRAZO_MINIMO_DIAS:
        return False, f"Prazo mínimo {PRAZO_MINIMO_DIAS} dias"
    return True, None
