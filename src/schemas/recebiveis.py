from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class SimulacaoAntecipacao(BaseModel):
    valor_bruto_brl: Decimal
    prazo_dias: int
    taxa_mensal_pct: float
    taxa_periodo: float
    custo_antecipacao_brl: Decimal
    valor_liquido_brl: Decimal
    custo_efetivo_anual_pct: float
    elegivel: bool
    motivo_inelegivel: str | None = None


class SolicitacaoAntecipacao(BaseModel):
    run_id: str
    valor_bruto_brl: Decimal
    prazo_dias: int
    aceite_termos: bool


class RecebiveisPendente(BaseModel):
    run_id: str
    numero_contrato: str | None
    orgao_nome: str | None
    valor_contrato_brl: Decimal
    data_vencimento: str
    elegivel: bool
