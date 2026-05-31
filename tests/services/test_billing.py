"""BILLING_TENANT — quota, trial, feature gate, webhook, reset (serviço)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.api.billing_store import BillingStore, TenantBilling
from src.services.billing import (
    apply_stripe_event,
    evaluate_quota,
    feature_decision,
    reset_usage_monthly,
)

_NOW = datetime(2026, 6, 1, 12, 0)


def test_at001_quota_atingida_starter():
    b = TenantBilling(tenant_id="t1", plan="starter", subscription_status="active", usage_analises_mes=20)
    d = evaluate_quota(b, _NOW)
    assert d.allowed is False
    assert d.status_code == 402
    assert d.error == "quota_exceeded"
    assert d.detail["limite"] == 20
    assert "upgrade_url" in d.detail


def test_at002_trial_valido():
    b = TenantBilling(tenant_id="t1", plan="trial", subscription_status="trial",
                      trial_ends_at=_NOW + timedelta(days=1), usage_analises_mes=2)
    d = evaluate_quota(b, _NOW)
    assert d.allowed is True


def test_at003_trial_expirado():
    b = TenantBilling(tenant_id="t1", plan="trial", subscription_status="trial",
                      trial_ends_at=_NOW - timedelta(days=1))
    d = evaluate_quota(b, _NOW)
    assert d.allowed is False
    assert d.status_code == 402
    assert d.error == "trial_expired"


def test_assinatura_inativa():
    b = TenantBilling(tenant_id="t1", plan="starter", subscription_status="canceled")
    d = evaluate_quota(b, _NOW)
    assert d.allowed is False
    assert d.error == "subscription_inactive"


def test_business_ilimitado():
    b = TenantBilling(tenant_id="t1", plan="business", subscription_status="active", usage_analises_mes=9999)
    assert evaluate_quota(b, _NOW).allowed is True


def test_at007_feature_gate_starter():
    b = TenantBilling(tenant_id="t1", plan="starter", subscription_status="active")
    d = feature_decision(b, "proposta")
    assert d.allowed is False
    assert d.status_code == 403
    assert "profissional" in d.detail["message"].lower()


def test_feature_disponivel_no_business():
    b = TenantBilling(tenant_id="t1", plan="business", subscription_status="active")
    assert feature_decision(b, "multi_cnpj").allowed is True


def test_at004_webhook_paid_ativa_e_reseta():
    b = TenantBilling(tenant_id="t1", plan="starter", subscription_status="past_due", usage_analises_mes=15)
    event = {
        "type": "invoice.paid",
        "data": {"object": {"subscription": "sub_123", "metadata": {"plan": "profissional"}}},
    }
    apply_stripe_event(b, event, _NOW)
    assert b.subscription_status == "active"
    assert b.usage_analises_mes == 0
    assert b.plan == "profissional"
    assert b.stripe_subscription_id == "sub_123"


def test_at005_webhook_cancelamento():
    b = TenantBilling(tenant_id="t1", plan="business", subscription_status="active")
    apply_stripe_event(b, {"type": "customer.subscription.deleted", "data": {"object": {}}}, _NOW)
    assert b.subscription_status == "canceled"


def test_webhook_payment_failed():
    b = TenantBilling(tenant_id="t1", plan="starter", subscription_status="active")
    apply_stripe_event(b, {"type": "invoice.payment_failed", "data": {"object": {}}}, _NOW)
    assert b.subscription_status == "past_due"


@pytest.mark.asyncio
async def test_at006_reset_mensal():
    store = BillingStore()
    await store.set(TenantBilling(tenant_id="a", subscription_status="active", usage_analises_mes=50))
    await store.set(TenantBilling(tenant_id="b", subscription_status="trial", usage_analises_mes=5))
    await store.set(TenantBilling(tenant_id="c", subscription_status="canceled", usage_analises_mes=10))

    n = await reset_usage_monthly(store, _NOW)
    assert n == 2  # active + trial; canceled não reseta
    assert (await store.get("a")).usage_analises_mes == 0
    assert (await store.get("c")).usage_analises_mes == 10
