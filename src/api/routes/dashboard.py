"""DASHBOARD_COCKPIT_V2 — KPIs agregados e pipeline Kanban.

O RunStore é em memória; o `stage` do Kanban é derivado de `current_step` e pode
ser sobrescrito por ``PATCH /pipeline/{run_id}/stage`` (drag-and-drop). Sem
migration — o override vive no RunEntry.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import require_role
from src.api.deps import get_store
from src.api.models import (
    DashboardSummary,
    FinanceSummary,
    PipelineCounts,
    PipelineItem,
    StageUpdate,
    _serialize,
)
from src.api.store import RunEntry, RunStore

router = APIRouter()

# current_step → stage padrão do Kanban (override manual tem precedência).
_STAGE_BY_STEP = {
    "start": "analisando",
    "ingestion": "analisando",
    "understanding": "analisando",
    "validated": "analisando",
    "decided": "decidindo",
    "completed": "preparando",
    "rejected": "perdido",
    "ingestion_failed": "perdido",
    "understanding_failed": "perdido",
    "execution_failed": "perdido",
}


def _effective_stage(entry: RunEntry) -> str:
    if entry.stage:
        return entry.stage
    step = entry.snapshot.get("current_step", "start")
    return _STAGE_BY_STEP.get(step, "analisando")


def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _valor(snapshot: dict) -> float:
    tender = _serialize(snapshot.get("tender_schema")) or {}
    if tender.get("valor_estimado") is not None:
        return _to_float(tender["valor_estimado"])
    pricing = _serialize(snapshot.get("pricing")) or {}
    return _to_float(pricing.get("recommended_price"))


def _deadline(snapshot: dict) -> str | None:
    tender = _serialize(snapshot.get("tender_schema")) or {}
    return tender.get("data_encerramento")


def _to_pipeline_item(entry: RunEntry) -> PipelineItem:
    snap = entry.snapshot
    tender = _serialize(snap.get("tender_schema")) or {}
    bid = _serialize(snap.get("bid_decision")) or {}
    return PipelineItem(
        run_id=entry.run_id,
        edital_id=snap.get("edital_id", ""),
        orgao=tender.get("orgao", "") or "",
        objeto=tender.get("objeto", "") or "",
        valor_estimado_brl=_valor(snap),
        stage=_effective_stage(entry),  # type: ignore[arg-type]
        bid_score=bid.get("confidence"),
        created_at=snap.get("created_at"),
        deadline=_deadline(snap),
    )


def _days_until(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        return (date.fromisoformat(iso_date[:10]) - date.today()).days
    except ValueError:
        return None


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entries = await store.all_entries()

    counts = PipelineCounts()
    finance = FinanceSummary()
    criticos = 0
    warning = 0

    for entry in entries:
        stage = _effective_stage(entry)
        snap = entry.snapshot

        if stage == "analisando":
            counts.analisando += 1
        elif stage == "decidindo":
            counts.decidindo += 1
            criticos += 1  # aguardando decisão humana = ação crítica
        elif stage == "preparando":
            counts.preparando += 1
        elif stage == "disputando":
            counts.disputando += 1
        elif stage == "ganho":
            counts.ganho_mes += 1
            valor = _valor(snap)
            finance.receita_contratada_brl += valor
            dias = _days_until(_deadline(snap))
            if dias is not None and dias >= 0:
                if dias <= 30:
                    finance.a_receber_30d_brl += valor
                elif dias <= 60:
                    finance.a_receber_60d_brl += valor
        elif stage == "perdido":
            counts.perdido_mes += 1

        if snap.get("errors"):
            warning += 1

    decididos = counts.ganho_mes + counts.perdido_mes
    taxa = (counts.ganho_mes / decididos * 100.0) if decididos else 0.0

    return DashboardSummary(
        pipeline=counts,
        financeiro=finance,
        taxa_vitoria_pct=round(taxa, 1),
        alertas_criticos=criticos,
        alertas_warning=warning,
    )


@router.get("/pipeline", response_model=list[PipelineItem])
async def list_pipeline(
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entries = await store.all_entries()
    return [_to_pipeline_item(e) for e in entries]


@router.patch("/pipeline/{run_id}/stage", response_model=PipelineItem)
async def update_stage(
    run_id: str,
    body: StageUpdate,
    store: RunStore = Depends(get_store),
    _auth=Depends(require_role("user", "operator")),
):
    entry = await store.set_stage(run_id, body.stage)
    if entry is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _to_pipeline_item(entry)
