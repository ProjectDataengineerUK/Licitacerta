"""Endpoints admin /admin/* — backoffice interno LicitaCerta."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.api.admin_audit_store import AdminAuditStore, AuditEntry
from src.api.deps import (
    get_admin_audit_store,
    get_billing_store,
    get_feature_flag_store,
    get_store,
    get_tenant_state_store,
)
from src.api.feature_flag_store import FeatureFlag, FeatureFlagStore
from src.api.tenant_state_store import TenantState, TenantStateStore

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_email(request: Request) -> str:
    return getattr(request.state, "admin_email", "unknown")


# ── schemas ──────────────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    tenants_ativos: int
    runs_hoje: int
    runs_semana: int
    custo_llm_hoje_brl: float
    erros_24h: int
    alertas: list[dict[str, str]]


class TenantSummary(BaseModel):
    tenant_id: str
    blocked: bool
    runs_total: int
    created_at: str


class BlockRequest(BaseModel):
    reason: str | None = None


class FeaturePatchRequest(BaseModel):
    enabled: bool
    override: bool = False
    expires_at: str | None = None
    note: str | None = None


class ImpersonateResponse(BaseModel):
    token: str
    tenant_id: str
    expires_at: str


class LoginRequest(BaseModel):
    admin_key: str


# ── dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    request: Request,
    store=Depends(get_store),
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
):
    today = datetime.now(UTC).date().isoformat()
    week_ago = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    all_runs = await store.list_all()
    runs_hoje = sum(1 for r in all_runs if r.created_at and r.created_at[:10] == today)
    runs_semana = sum(1 for r in all_runs if r.created_at and r.created_at >= week_ago)
    erros_24h = sum(
        1 for r in all_runs
        if r.last_step in {"ingestion_failed", "understanding_failed", "execution_failed"}
        and r.created_at and r.created_at >= (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    )

    tenants_ativos = len({r.tenant_id for r in all_runs if not tenant_state_store.is_blocked(r.tenant_id)})

    alertas: list[dict[str, str]] = []
    if erros_24h > 5:
        alertas.append({"nivel": "critical", "mensagem": f"{erros_24h} erros nas últimas 24h"})

    return DashboardResponse(
        tenants_ativos=tenants_ativos,
        runs_hoje=runs_hoje,
        runs_semana=runs_semana,
        custo_llm_hoje_brl=0.0,
        erros_24h=erros_24h,
        alertas=alertas,
    )


# ── tenants ──────────────────────────────────────────────────────────────────

@router.get("/tenants", response_model=list[TenantSummary])
async def list_tenants(
    blocked: bool | None = Query(default=None),
    store=Depends(get_store),
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
):
    all_runs = await store.list_all()
    by_tenant: dict[str, list[Any]] = {}
    for r in all_runs:
        by_tenant.setdefault(r.tenant_id, []).append(r)

    states = {s.tenant_id: s for s in tenant_state_store.list_all()}

    result = []
    for tid, runs in by_tenant.items():
        state = states.get(tid)
        is_blocked = state.blocked if state else False
        if blocked is not None and is_blocked != blocked:
            continue
        earliest = min((r.created_at for r in runs if r.created_at), default="")
        result.append(TenantSummary(
            tenant_id=tid,
            blocked=is_blocked,
            runs_total=len(runs),
            created_at=earliest,
        ))

    return result


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    store=Depends(get_store),
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
    feature_flag_store: FeatureFlagStore = Depends(get_feature_flag_store),
    billing_store=Depends(get_billing_store),
):
    all_runs = await store.list_all()
    tenant_runs = [r for r in all_runs if r.tenant_id == tenant_id]
    state = tenant_state_store.get(tenant_id)
    features = feature_flag_store.list_for_tenant(tenant_id)
    billing = billing_store.get(tenant_id)

    return {
        "tenant_id": tenant_id,
        "blocked": state.blocked if state else False,
        "blocked_reason": state.blocked_reason if state else None,
        "runs_total": len(tenant_runs),
        "features": [f.model_dump() for f in features],
        "plan": billing.plan if billing else "free",
        "runs_this_month": len(tenant_runs),
    }


@router.post("/tenants/{tenant_id}/bloquear", response_model=TenantState)
async def bloquear_tenant(
    tenant_id: str,
    body: BlockRequest,
    request: Request,
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
    audit_store: AdminAuditStore = Depends(get_admin_audit_store),
):
    before = tenant_state_store.get(tenant_id)
    updated = tenant_state_store.block(tenant_id, body.reason, by=_admin_email(request))
    audit_store.append(
        admin_email=_admin_email(request),
        acao="bloquear_tenant",
        entidade_tipo="tenant",
        entidade_id=tenant_id,
        dados_antes=before.model_dump() if before else None,
        dados_depois=updated.model_dump(),
    )
    return updated


@router.post("/tenants/{tenant_id}/desbloquear", response_model=TenantState)
async def desbloquear_tenant(
    tenant_id: str,
    request: Request,
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
    audit_store: AdminAuditStore = Depends(get_admin_audit_store),
):
    before = tenant_state_store.get(tenant_id)
    updated = tenant_state_store.unblock(tenant_id)
    audit_store.append(
        admin_email=_admin_email(request),
        acao="desbloquear_tenant",
        entidade_tipo="tenant",
        entidade_id=tenant_id,
        dados_antes=before.model_dump() if before else None,
        dados_depois=updated.model_dump(),
    )
    return updated


# ── feature flags ─────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/features", response_model=list[FeatureFlag])
async def get_features(
    tenant_id: str,
    feature_flag_store: FeatureFlagStore = Depends(get_feature_flag_store),
):
    return feature_flag_store.list_for_tenant(tenant_id)


@router.patch("/tenants/{tenant_id}/features/{feature}", response_model=FeatureFlag)
async def patch_feature(
    tenant_id: str,
    feature: str,
    body: FeaturePatchRequest,
    request: Request,
    feature_flag_store: FeatureFlagStore = Depends(get_feature_flag_store),
    audit_store: AdminAuditStore = Depends(get_admin_audit_store),
):
    before = feature_flag_store.get(tenant_id, feature)
    updated = feature_flag_store.set(
        tenant_id=tenant_id,
        feature=feature,
        enabled=body.enabled,
        override=body.override,
        expires_at=body.expires_at,
        note=body.note,
        created_by=_admin_email(request),
    )
    acao = "habilitar_feature" if body.enabled else "desabilitar_feature"
    audit_store.append(
        admin_email=_admin_email(request),
        acao=acao,
        entidade_tipo="feature_flag",
        entidade_id=f"{tenant_id}:{feature}",
        dados_antes=before.model_dump() if before else None,
        dados_depois=updated.model_dump(),
    )
    return updated


# ── impersonation ─────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_tenant(
    tenant_id: str,
    request: Request,
    tenant_state_store: TenantStateStore = Depends(get_tenant_state_store),
    audit_store: AdminAuditStore = Depends(get_admin_audit_store),
):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    tenant_state_store.create_impersonation(
        token=token,
        tenant_id=tenant_id,
        admin_email=_admin_email(request),
        expires_at=expires_at,
    )
    audit_store.append(
        admin_email=_admin_email(request),
        acao="impersonation_start",
        entidade_tipo="tenant",
        entidade_id=tenant_id,
    )
    return ImpersonateResponse(token=token, tenant_id=tenant_id, expires_at=expires_at)


# ── audit log ────────────────────────────────────────────────────────────────

@router.get("/audit", response_model=list[AuditEntry])
async def get_audit(
    admin_email: str | None = Query(default=None),
    acao: str | None = Query(default=None),
    entidade_tipo: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    audit_store: AdminAuditStore = Depends(get_admin_audit_store),
):
    return audit_store.list(
        admin_email=admin_email,
        acao=acao,
        entidade_tipo=entidade_tipo,
        limit=limit,
    )


# ── métricas IA ───────────────────────────────────────────────────────────────

@router.get("/metricas/ia")
async def get_metricas_ia(store=Depends(get_store)):
    all_runs = await store.list_all()
    total = len(all_runs)
    if not total:
        return {"total_runs": 0, "taxa_hitl": 0.0, "distribuicao_steps": {}}

    step_counts: dict[str, int] = {}
    for r in all_runs:
        step_counts[r.last_step] = step_counts.get(r.last_step, 0) + 1

    decided = step_counts.get("decided", 0)
    taxa_hitl = round(decided / total, 4) if total else 0.0

    return {
        "total_runs": total,
        "taxa_hitl": taxa_hitl,
        "distribuicao_steps": step_counts,
    }


# ── debug de run ──────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/debug")
async def debug_run(run_id: str, store=Depends(get_store)):
    run = await store.get(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} não encontrado")
    return {
        "run_id": run_id,
        "last_step": run.last_step,
        "snapshot_keys": list(run.snapshot.keys()),
        "snapshot": run.snapshot,
    }


# ── login (sem autenticação — pública, mas sem expor estado) ──────────────────

@router.post("/login")
async def admin_login(body: LoginRequest):
    import hmac
    import os
    secret = os.getenv("ADMIN_SECRET_KEY", "")
    if not secret or not hmac.compare_digest(body.admin_key, secret):
        raise HTTPException(403, "Chave inválida")
    return {"ok": True, "message": "Chave válida — armazene em sessionStorage"}
