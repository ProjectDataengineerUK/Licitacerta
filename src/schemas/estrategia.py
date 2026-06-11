from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CategoriaAcao = Literal["documentacao", "precificacao", "juridico", "operacional", "inteligencia"]


class AcaoDireta(BaseModel):
    label: str
    rota: str


class AcaoEstrategica(BaseModel):
    numero: int
    categoria: CategoriaAcao
    titulo: str
    descricao: str
    prazo: str
    impacto_vitoria_pct: float
    acao_direta: AcaoDireta | None = None
    concluida: bool = False


class EstrategiaResult(BaseModel):
    probabilidade_sem_acoes_pct: float
    probabilidade_com_acoes_pct: float
    acoes: list[AcaoEstrategica] = []
    resumo_executivo: str
    data_insuficiente: bool = False
