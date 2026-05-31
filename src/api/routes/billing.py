"""BILLING_TENANT — endpoints de planos, uso e webhook Stripe."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.auth import require_role
from src.api.billing_store import BillingStore
from src.api.deps import get_billing_store
from src.services.billing import PLANS, apply_stripe_event, get_plan

router = APIRouter()


class PlanOut(BaseModel):
    nome: str
    preco_mensal_brl: float
    quota_analises_mes: int | None
    quota_cnpjs: int | None
    quota_portais: int | None
    feature_proposta: bool
    feature_contract_agent: bool
    feature_api_access: bool
    feature_multi_cnpj: bool


class UsageOut(BaseModel):
    plan: str
    subscription_status: str
    usado: int
    limite: int | None
    reset_em: str | None


@router.get("/billing/plans", response_model=list[PlanOut])
async def list_plans(_auth=Depends(require_role("user", "operator"))):
    return [
        PlanOut(
            nome=p.nome, preco_mensal_brl=p.preco_mensal_brl,
            quota_analises_mes=p.quota_analises_mes, quota_cnpjs=p.quota_cnpjs,
            quota_portais=p.quota_portais, feature_proposta=p.feature_proposta,
            feature_contract_agent=p.feature_contract_agent,
            feature_api_access=p.feature_api_access, feature_multi_cnpj=p.feature_multi_cnpj,
        )
        for p in PLANS.values() if p.nome != "trial"
    ]


@router.get("/billing/usage", response_model=UsageOut)
async def get_usage(
    tenant_id: str = Query(...),
    store: BillingStore = Depends(get_billing_store),
    _auth=Depends(require_role("user", "operator")),
):
    billing = await store.get_or_create_trial(tenant_id)
    plan = get_plan(billing.plan)
    return UsageOut(
        plan=billing.plan,
        subscription_status=billing.subscription_status,
        usado=billing.usage_analises_mes,
        limite=plan.quota_analises_mes,
        reset_em=billing.usage_reset_at.isoformat() if billing.usage_reset_at else None,
    )


@router.post("/billing/webhook")
async def stripe_webhook(
    event: dict,
    store: BillingStore = Depends(get_billing_store),
):
    obj = (event.get("data") or {}).get("object") or {}
    metadata = obj.get("metadata") or {}

    billing = None
    if metadata.get("tenant_id"):
        billing = await store.get_or_create_trial(metadata["tenant_id"])
    elif obj.get("subscription"):
        billing = await store.get_by_subscription_id(obj["subscription"])
    elif obj.get("customer"):
        billing = await store.get_by_customer_id(obj["customer"])

    if billing is None:
        raise HTTPException(status_code=404, detail="tenant não encontrado para o evento")

    apply_stripe_event(billing, event)
    await store.set(billing)
    return {"status": "processed", "subscription_status": billing.subscription_status}


@router.post("/billing/checkout")
async def create_checkout(
    tenant_id: str = Query(...),
    plan: str = Query(...),
    _auth=Depends(require_role("user", "operator")),
):
    if plan not in PLANS or plan == "trial":
        raise HTTPException(status_code=422, detail="plano inválido")
    if not os.environ.get("STRIPE_SECRET_KEY"):
        # Stripe não configurado — stub (feature-flag); integração real é follow-up
        return {"checkout_url": None, "status": "stripe_not_configured"}
    raise HTTPException(status_code=501, detail="Stripe checkout real ainda não implementado")
