from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class MesCashflow(BaseModel):
    mes: int
    entrada_brl: Decimal
    saida_brl: Decimal
    saldo_acumulado_brl: Decimal
    positivo: bool


class SugestaoMitigacao(BaseModel):
    tipo: Literal["antecipacao_recebiveis", "adiantamento_contratual", "ajuste_proposta"]
    descricao: str
    impacto_brl: Decimal
    custo_brl: Decimal | None = None


class CashflowSimulation(BaseModel):
    valor_mensal_brl: Decimal
    custo_mensal_brl: Decimal
    prazo_pagamento_dias: int
    duracao_meses: int
    caixa_inicial_brl: Decimal
    meses: list[MesCashflow]
    saldo_minimo_brl: Decimal
    capital_giro_necessario_brl: Decimal
    risco: Literal["ok", "atencao", "critico"]
    mes_critico: int | None
    sugestoes: list[SugestaoMitigacao]
    cenario_atraso_30d: CashflowSimulation | None = None


CashflowSimulation.model_rebuild()
