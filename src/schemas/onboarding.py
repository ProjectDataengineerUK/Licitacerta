from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DicaCategoria(str, Enum):
    INICIO = "inicio"
    ANALISE = "analise"
    DECISAO = "decisao"
    PROPOSTA = "proposta"
    FINANCEIRO = "financeiro"


class CoachDica(BaseModel):
    id: str
    titulo: str
    descricao: str
    categoria: DicaCategoria
    rota_sugerida: str | None = None
    ordem: int


class OnboardingProgress(BaseModel):
    tenant_id: str
    dicas_vistas: list[str] = []
    dicas_dispensadas: list[str] = []
    pct_concluido: float = 0.0
    proxima_dica: CoachDica | None = None


class MarcarVistaBody(BaseModel):
    dica_id: str
    dispensar: bool = False
