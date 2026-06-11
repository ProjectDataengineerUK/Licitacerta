from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class Oportunidade(BaseModel):
    run_id: str
    titulo: str | None = None
    orgao: str | None = None
    valor_estimado_brl: Decimal
    bid_no_bid_score: float
    probabilidade_vitoria_pct: float
    custo_estimado_brl: Decimal
    prazo_pagamento_dias: int
    data_sessao: str | None = None
    capacidade_necessaria_pct: float


class ResultadoCenario(BaseModel):
    nome: Literal["Conservador", "Moderado", "Agressivo"]
    oportunidades_selecionadas: list[str]
    valor_total_brl: Decimal
    custo_total_brl: Decimal
    capital_comprometido_brl: Decimal
    valor_esperado_ponderado_brl: Decimal
    probabilidade_vitoria_media_pct: float
    capacidade_utilizada_pct: float
    roi_esperado_pct: float


class PortfolioOtimizacaoInput(BaseModel):
    oportunidades: list[Oportunidade]
    capital_giro_disponivel_brl: Decimal
    capacidade_maxima_pct: float = 100.0
    capacidade_atual_pct: float = 0.0
    max_contratos_simultaneos: int = 5


class PortfolioOtimizacaoResult(BaseModel):
    conservador: ResultadoCenario
    moderado: ResultadoCenario
    agressivo: ResultadoCenario
    oportunidades_rejeitadas: list[str]
    resumo: str
