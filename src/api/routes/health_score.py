"""SCORE_SAUDE_OPERACAO — endpoint do score de saúde operacional."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from src.api.auth import require_role
from src.api.contract_store import ContractStore
from src.api.deps import get_contract_store, get_store
from src.api.store import RunStore
from src.schemas.health import HealthScore, ScoreInputs
from src.services.health_score import calcular_score

router = APIRouter()

_GANHO_PERDIDO = {"ganho", "perdido"}


def _effective_stage(entry) -> str:
    if entry.stage:
        return entry.stage
    step = entry.snapshot.get("current_step", "start")
    return {"decided": "decidindo", "completed": "preparando", "rejected": "perdido"}.get(step, "analisando")


async def _build_inputs(
    store: RunStore, contracts: ContractStore, previous_score: int | None
) -> ScoreInputs:
    # NOTA (follow-up): RunEntry ainda não expõe created_at, então não há como
    # filtrar a janela de 90/30 dias aqui — usamos todo o histórico como proxy.
    # Quando o RunStore migrar para AlloyDB (com timestamps), aplicar o filtro.
    entries = await store.all_entries()
    ganhos = sum(1 for e in entries if _effective_stage(e) == "ganho")
    perdidos = sum(1 for e in entries if _effective_stage(e) == "perdido")

    contratos = await contracts.list()
    hoje = date.today()
    contratos_criticos = sum(
        1 for c in contratos
        if c.status in ("ativo", "renovado") and 0 <= (c.data_vencimento - hoje).days <= 30
    )
    empenhos_atrasados = sum(
        1 for c in contratos for e in c.empenhos
        if e.status in ("emitido", "liquidado") and (hoje - e.data_emissao).days > c.prazo_pagamento_dias
    )
    # concentração: maior fatia de valor entre contratos ativos por órgão
    por_orgao: dict[str, float] = {}
    for c in contratos:
        if c.status in ("ativo", "renovado"):
            por_orgao[c.orgao_cnpj] = por_orgao.get(c.orgao_cnpj, 0.0) + c.valor_atual_brl
    total_valor = sum(por_orgao.values())
    concentracao = (max(por_orgao.values()) / total_valor) if total_valor > 0 else 0.0

    return ScoreInputs(
        runs_ganhos_90d=ganhos,
        runs_total_90d=ganhos + perdidos,
        tem_analise_recente_30d=len(entries) > 0,
        contratos_criticos=contratos_criticos,
        empenhos_atrasados=empenhos_atrasados,
        concentracao_orgao=concentracao,
        previous_score=previous_score,
    )


@router.get("/health-score", response_model=HealthScore)
async def health_score(
    previous_score: int | None = Query(default=None),
    store: RunStore = Depends(get_store),
    contracts: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    inputs = await _build_inputs(store, contracts, previous_score)
    return calcular_score(inputs)
