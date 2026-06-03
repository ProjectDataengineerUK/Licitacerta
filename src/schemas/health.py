"""SCORE_SAUDE_OPERACAO — schemas do score de saúde operacional."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponenteStatus = Literal["otimo", "bom", "atencao", "critico"]
ScoreLabel = Literal["Excelente", "Bom", "Atenção", "Crítico"]


class ScoreInputs(BaseModel):
    """Indicadores já agregados (o cálculo não faz queries)."""

    runs_ganhos_90d: int = 0
    runs_total_90d: int = 0  # ganhos + perdidos
    tem_analise_recente_30d: bool = False
    contratos_criticos: int = 0           # vencendo em 30d sem ação
    certidoes_vencendo_15d: int = 0
    certidoes_vencidas: int = 0
    empenhos_atrasados: int = 0
    concentracao_orgao: float = Field(default=0.0, ge=0.0, le=1.0)  # fração no maior órgão
    previous_score: int | None = Field(default=None, ge=0, le=100)


class ComponenteScore(BaseModel):
    nome: str
    valor: float
    peso: float
    contribuicao: float
    descricao: str
    status: ComponenteStatus


class Recomendacao(BaseModel):
    prioridade: int
    titulo: str
    acao: str
    link: str | None = None
    impacto_no_score: float


class HealthScore(BaseModel):
    score: int
    label: ScoreLabel
    componentes: list[ComponenteScore] = []
    recomendacoes: list[Recomendacao] = []
    delta_semana: int | None = None
    calculado_em: datetime = Field(default_factory=datetime.now)
