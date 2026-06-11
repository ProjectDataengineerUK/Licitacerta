from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

NivelDirecionamento = Literal["baixo", "medio", "alto"]


class SinalDetectado(BaseModel):
    codigo: str
    descricao: str
    peso: float
    evidencia: str


class DirecionamentoResult(BaseModel):
    score: float
    nivel: NivelDirecionamento
    sinais_detectados: list[SinalDetectado] = []
    sinais_cartel: list[SinalDetectado] = []
    fingerprint_beneficiario: str | None = None
    recomendacao: str
    fundamentacao_impugnacao: str | None = None
    precedentes_tcu: list[str] = []
    impugnacao_recomendada: bool = False
