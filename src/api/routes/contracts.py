"""GESTAO_CONTRATOS_FULL — CRUD de contratos, empenhos, SRP, dashboard e alertas."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.auth import require_role
from src.api.contract_store import (
    Contract,
    ContractCreate,
    ContractPatch,
    ContractStore,
    Convocacao,
    ConvocacaoCreate,
    Empenho,
    EmpenhoCreate,
    EmpenhoPatch,
)
from src.api.deps import get_contract_store, get_reajuste_service
from src.services.reajuste import ReajusteService

router = APIRouter()

_VENCIMENTO_BUCKETS = (15, 30, 60, 90)


class ContractDashboard(BaseModel):
    total_contratado_brl: float = 0.0
    recebido_brl: float = 0.0
    a_receber_brl: float = 0.0
    em_atraso_brl: float = 0.0
    vencendo_30d: int = 0


class ContractAlert(BaseModel):
    contract_id: str
    tipo: str  # vencimento_contrato | pagamento_atrasado
    severity: str  # critical | warning | info
    mensagem: str
    prazo_dias: int | None = None
    acao_sugerida: str


class ReajusteResponse(BaseModel):
    valor_base_brl: float
    novo_valor_brl: float
    variacao_pct: float
    indice: str
    fonte: str


def _days_until(d: date | None) -> int | None:
    return (d - date.today()).days if d else None


# --------------------------------------------------------------------------- #
# Rotas estáticas (antes de /{contract_id} para não colidir)
# --------------------------------------------------------------------------- #
@router.get("/contracts/dashboard", response_model=ContractDashboard)
async def contracts_dashboard(
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    contracts = await store.list()
    dash = ContractDashboard()
    for c in contracts:
        if c.status in ("ativo", "renovado"):
            dash.total_contratado_brl += c.valor_atual_brl
            dias = _days_until(c.data_vencimento)
            if dias is not None and 0 <= dias <= 30:
                dash.vencendo_30d += 1
        for e in c.empenhos:
            if e.status == "pago":
                dash.recebido_brl += e.valor_brl
            elif e.status in ("emitido", "liquidado"):
                dash.a_receber_brl += e.valor_brl
                atraso = _days_until(e.data_emissao)
                if atraso is not None and -atraso > c.prazo_pagamento_dias:
                    dash.em_atraso_brl += e.valor_brl
    return dash


class FinanceiroTrendMonth(BaseModel):
    mes: str  # "YYYY-MM"
    contratado_brl: float = 0.0
    recebido_brl: float = 0.0
    a_receber_brl: float = 0.0


class FinanceiroTrend(BaseModel):
    months: list[FinanceiroTrendMonth] = []


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _last_months(n: int) -> list[str]:
    today = date.today()
    keys = []
    year, month = today.year, today.month
    for _ in range(n):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


@router.get("/financeiro/trend", response_model=FinanceiroTrend)
async def financeiro_trend(
    months: int = Query(default=6, ge=1, le=24),
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    """Série mensal real de contratado/recebido/a receber — alimenta o gráfico do Cockpit."""
    keys = _last_months(months)
    buckets = {k: FinanceiroTrendMonth(mes=k) for k in keys}
    for c in await store.list():
        k = _month_key(c.data_inicio)
        if k in buckets and c.status in ("ativo", "renovado", "encerrado"):
            buckets[k].contratado_brl += c.valor_atual_brl or c.valor_original_brl
        for e in c.empenhos:
            if e.status == "pago" and e.data_pagamento:
                kp = _month_key(e.data_pagamento)
                if kp in buckets:
                    buckets[kp].recebido_brl += e.valor_brl
            elif e.status in ("emitido", "liquidado"):
                ke = _month_key(e.data_emissao)
                if ke in buckets:
                    buckets[ke].a_receber_brl += e.valor_brl
    return FinanceiroTrend(months=[buckets[k] for k in keys])


@router.get("/contracts/alerts", response_model=list[ContractAlert])
async def contracts_alerts(
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    alerts: list[ContractAlert] = []
    for c in await store.list():
        if c.status in ("ativo", "renovado"):
            dias = _days_until(c.data_vencimento)
            if dias is not None and 0 <= dias <= 90:
                severity = "critical" if dias <= 15 else "warning" if dias <= 30 else "info"
                alerts.append(ContractAlert(
                    contract_id=c.id,
                    tipo="vencimento_contrato",
                    severity=severity,
                    mensagem=f"Contrato {c.numero_contrato or c.id} vence em {dias} dias",
                    prazo_dias=dias,
                    acao_sugerida="renovar ou encerrar",
                ))
        for e in c.empenhos:
            if e.status in ("emitido", "liquidado"):
                desde = _days_until(e.data_emissao)
                if desde is not None and -desde > c.prazo_pagamento_dias:
                    alerts.append(ContractAlert(
                        contract_id=c.id,
                        tipo="pagamento_atrasado",
                        severity="critical",
                        mensagem=f"Empenho {e.numero_empenho} sem pagamento há {-desde} dias",
                        prazo_dias=-desde,
                        acao_sugerida="gerar notificação de inadimplência",
                    ))
    return alerts


@router.post("/contracts", response_model=Contract, status_code=201)
async def create_contract(
    body: ContractCreate,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    return await store.create(body)


@router.get("/contracts", response_model=list[Contract])
async def list_contracts(
    status: str | None = Query(default=None),
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    return await store.list(status=status)


# --------------------------------------------------------------------------- #
# Rotas por contrato
# --------------------------------------------------------------------------- #
@router.get("/contracts/{contract_id}", response_model=Contract)
async def get_contract(
    contract_id: str,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    c = await store.get(contract_id)
    if c is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return c


@router.patch("/contracts/{contract_id}", response_model=Contract)
async def patch_contract(
    contract_id: str,
    body: ContractPatch,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    c = await store.patch(contract_id, body)
    if c is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return c


@router.delete("/contracts/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: str,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    ok = await store.delete(contract_id)
    if not ok:
        raise HTTPException(status_code=404, detail="contract not found")


@router.post("/contracts/{contract_id}/empenhos", response_model=Empenho, status_code=201)
async def add_empenho(
    contract_id: str,
    body: EmpenhoCreate,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    emp = await store.add_empenho(contract_id, body)
    if emp is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return emp


@router.patch("/contracts/{contract_id}/empenhos/{empenho_id}", response_model=Empenho)
async def patch_empenho(
    contract_id: str,
    empenho_id: str,
    body: EmpenhoPatch,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    emp = await store.patch_empenho(contract_id, empenho_id, body)
    if emp is None:
        raise HTTPException(status_code=404, detail="contract or empenho not found")
    return emp


@router.post("/contracts/{contract_id}/srp", response_model=Convocacao, status_code=201)
async def add_convocacao(
    contract_id: str,
    body: ConvocacaoCreate,
    store: ContractStore = Depends(get_contract_store),
    _auth=Depends(require_role("user", "operator")),
):
    conv = await store.add_convocacao(contract_id, body)
    if conv is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return conv


@router.get("/contracts/{contract_id}/reajuste", response_model=ReajusteResponse)
async def calcular_reajuste(
    contract_id: str,
    data_reajuste: date | None = Query(default=None),
    store: ContractStore = Depends(get_contract_store),
    service: ReajusteService = Depends(get_reajuste_service),
    _auth=Depends(require_role("user", "operator")),
):
    c = await store.get(contract_id)
    if c is None:
        raise HTTPException(status_code=404, detail="contract not found")
    if not c.indice_reajuste or not c.data_base:
        raise HTTPException(status_code=409, detail="contrato sem índice/data base de reajuste")

    alvo = data_reajuste or date.today()
    try:
        async with service:
            result = await service.calcular(
                Decimal(str(c.valor_atual_brl)), c.indice_reajuste, c.data_base, alvo
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ReajusteResponse(
        valor_base_brl=float(result.valor_base_brl),
        novo_valor_brl=float(result.novo_valor_brl),
        variacao_pct=result.variacao_pct,
        indice=result.indice,
        fonte=result.fonte,
    )
