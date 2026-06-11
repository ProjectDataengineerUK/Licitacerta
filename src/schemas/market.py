from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CompetitorProfile(BaseModel):
    cnpj: str
    nome: str | None = None
    taxa_vitoria_pct: float
    total_vitorias: int
    top_orgaos: list[str] = []
    preco_medio_brl: Decimal | None = None
    ultima_participacao: date | None = None
    dominante: bool = False


class PriceBenchmark(BaseModel):
    item_descricao: str
    match_method: Literal["catmat", "trigram"] = "catmat"
    match_confidence: float = 1.0
    amostra: int
    media_brl: Decimal | None = None
    min_brl: Decimal | None = None
    max_brl: Decimal | None = None
    percentil_25: Decimal | None = None
    percentil_75: Decimal | None = None
    tendencia_12m_pct: float | None = None
    data_insuficiente: bool = False


class OrganScore(BaseModel):
    uasg: str | None = None
    orgao_cnpj: str
    orgao_nome: str | None = None
    score: int
    label: Literal["Bom Pagador", "Regular", "Risco Alto"]
    prazo_medio_pagamento_dias: int | None = None
    indice_inadimplencia_pct: float | None = None
    nivel_exigencia: Literal["baixo", "medio", "alto"] = "medio"
    amostra: int
    alerta_inadimplencia: bool = False
    data_insuficiente: bool = False


class CompetitiveContext(BaseModel):
    """Injetado no PricingAgent e BidNoBidAgent via decision_subgraph."""

    segmento_cnae: str | None = None
    top_competitors: list[CompetitorProfile] = []
    price_benchmark: PriceBenchmark | None = None
    organ_score: OrganScore | None = None
    concentracao_alta: bool = False
    cnpj_dominante: str | None = None
    resumo: str = ""
    data_insuficiente: bool = False
