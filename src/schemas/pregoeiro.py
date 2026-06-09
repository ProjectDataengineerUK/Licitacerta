from __future__ import annotations

from pydantic import BaseModel


class EmpresaFrequente(BaseModel):
    cnpj: str
    nome: str | None = None
    frequencia: int


class PregoeiroPerfil(BaseModel):
    nome: str
    orgao_cnpj: str
    orgao_nome: str | None = None
    total_sessoes: int = 0
    indice_reputacao: float | None = None
    confianca_pct: float = 0.0
    label_confianca: str = "Sem dados"
    taxa_aceitacao_impugnacao_pct: float | None = None
    taxa_desclassificacao_pct: float | None = None
    tempo_medio_sessao_horas: float | None = None
    previsibilidade: float | None = None
    clausulas_frequentes: list[str] = []
    tipos_desclassificacao: list[str] = []
    empresas_frequentes_vencedoras: list[EmpresaFrequente] = []
    alertas: list[str] = []
