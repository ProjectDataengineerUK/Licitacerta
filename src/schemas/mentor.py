from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

TipoResposta = Literal["juridico", "financeiro", "operacional", "estrategico", "geral"]


class AcaoSugerida(BaseModel):
    label: str
    rota: str | None = None


class EvidenciaMentor(BaseModel):
    trecho: str
    pagina: int | None = None
    fonte: str | None = None


class MentorMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    tipo_resposta: TipoResposta | None = None
    acoes_sugeridas: list[AcaoSugerida] = []
    evidencias: list[EvidenciaMentor] = []
    disclaimer: str | None = None


class MentorResponse(BaseModel):
    resposta: str
    tipo_resposta: TipoResposta
    acoes_sugeridas: list[AcaoSugerida] = []
    evidencias: list[EvidenciaMentor] = []
    confianca: float
    disclaimer: str | None = None
