"""BILLING_TENANT — planos, avaliação de quota e processamento de webhook Stripe.

Lógica determinística e pura (testável). Integração real com Stripe (checkout,
portal, verificação de assinatura) fica atrás de interface/feature-flag.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.api.billing_store import BillingStore, TenantBilling

_UPGRADE_URL = "https://app.licitacerta.com.br/billing/upgrade"


@dataclass(frozen=True)
class Plan:
    nome: str
    preco_mensal_brl: float
    quota_analises_mes: int | None  # None = ilimitado
    quota_cnpjs: int | None
    quota_portais: int | None
    feature_proposta: bool = False
    feature_contract_agent: bool = False
    feature_api_access: bool = False
    feature_multi_cnpj: bool = False
    trial_dias: int = 7
    stripe_price_id: str | None = None


PLANS: dict[str, Plan] = {
    "trial": Plan("trial", 0.0, 10, 1, 1, trial_dias=7),
    "starter": Plan("starter", 149.0, 20, 1, 1),
    "profissional": Plan("profissional", 299.0, 100, 1, 3,
                         feature_proposta=True, feature_contract_agent=True),
    "business": Plan("business", 599.0, None, 3, None,
                     feature_proposta=True, feature_contract_agent=True, feature_multi_cnpj=True),
    "enterprise": Plan("enterprise", 1499.0, None, None, None,
                       feature_proposta=True, feature_contract_agent=True,
                       feature_api_access=True, feature_multi_cnpj=True),
}


@dataclass
class QuotaDecision:
    allowed: bool
    status_code: int = 200
    error: str | None = None
    detail: dict | None = None


def get_plan(nome: str | None) -> Plan:
    return PLANS.get((nome or "trial").lower(), PLANS["trial"])


def evaluate_quota(billing: TenantBilling, now: datetime | None = None) -> QuotaDecision:
    """Decide se o tenant pode iniciar uma nova análise."""
    now = now or datetime.now()
    plan = get_plan(billing.plan)
    status = billing.subscription_status

    if status == "trial":
        if billing.trial_ends_at is not None and now > billing.trial_ends_at:
            return QuotaDecision(False, 402, "trial_expired",
                                 {"message": "Trial expirado. Escolha um plano.", "upgrade_url": _UPGRADE_URL})
        return _check_limit(billing, plan)

    if status == "active":
        return _check_limit(billing, plan)

    # canceled / past_due / paused
    return QuotaDecision(False, 402, "subscription_inactive",
                         {"message": "Assinatura inativa. Renove em /billing", "status": status})


def _check_limit(billing: TenantBilling, plan: Plan) -> QuotaDecision:
    limit = plan.quota_analises_mes
    if limit is not None and billing.usage_analises_mes >= limit:
        return QuotaDecision(False, 402, "quota_exceeded",
                             {"usado": billing.usage_analises_mes, "limite": limit, "upgrade_url": _UPGRADE_URL})
    return QuotaDecision(True)


def feature_decision(billing: TenantBilling, feature: str) -> QuotaDecision:
    """403 quando a feature não está disponível no plano do tenant."""
    plan = get_plan(billing.plan)
    if getattr(plan, f"feature_{feature}", False):
        return QuotaDecision(True)
    # menor plano que habilita a feature
    upgrade = next((p.nome for p in PLANS.values() if getattr(p, f"feature_{feature}", False)), "profissional")
    return QuotaDecision(False, 403, "feature_unavailable",
                         {"feature": feature, "message": f"Disponível no plano {upgrade}", "upgrade_url": _UPGRADE_URL})


def apply_stripe_event(billing: TenantBilling, event: dict, now: datetime | None = None) -> TenantBilling:
    """Aplica um evento Stripe ao estado de billing do tenant."""
    now = now or datetime.now()
    tipo = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if tipo in ("invoice.paid", "customer.subscription.created", "customer.subscription.updated"):
        billing.subscription_status = "active"
        billing.usage_analises_mes = 0
        billing.usage_reset_at = now
        metadata = obj.get("metadata") or {}
        if metadata.get("plan"):
            billing.plan = metadata["plan"]
        if obj.get("customer"):
            billing.stripe_customer_id = obj["customer"]
        if obj.get("subscription") or obj.get("id"):
            billing.stripe_subscription_id = obj.get("subscription") or obj.get("id")
    elif tipo == "customer.subscription.deleted":
        billing.subscription_status = "canceled"
    elif tipo == "invoice.payment_failed":
        billing.subscription_status = "past_due"

    return billing


async def reset_usage_monthly(store: BillingStore, now: datetime | None = None) -> int:
    """Zera o contador mensal dos tenants ativos/trial. Chamado por job mensal."""
    now = now or datetime.now()
    reset = 0
    for billing in await store.all():
        if billing.subscription_status in ("active", "trial"):
            billing.usage_analises_mes = 0
            billing.usage_reset_at = now
            reset += 1
    return reset
