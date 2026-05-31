"""BILLING_TENANT — estado de billing por tenant (in-memory).

Migration AlloyDB (`plans` + colunas em `tenants`) é follow-up.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

SubscriptionStatus = Literal["trial", "active", "past_due", "canceled", "paused"]


class TenantBilling(BaseModel):
    tenant_id: str
    plan: str = "trial"
    subscription_status: SubscriptionStatus = "trial"
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    usage_analises_mes: int = 0
    usage_reset_at: datetime | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class BillingStore:
    def __init__(self) -> None:
        self._by_tenant: dict[str, TenantBilling] = {}
        self._lock = asyncio.Lock()

    async def create_trial(self, tenant_id: str, trial_days: int = 7) -> TenantBilling:
        async with self._lock:
            billing = TenantBilling(
                tenant_id=tenant_id,
                plan="trial",
                subscription_status="trial",
                trial_ends_at=datetime.now() + timedelta(days=trial_days),
            )
            self._by_tenant[tenant_id] = billing
            return billing

    async def get(self, tenant_id: str) -> TenantBilling | None:
        async with self._lock:
            return self._by_tenant.get(tenant_id)

    async def get_or_create_trial(self, tenant_id: str, trial_days: int = 7) -> TenantBilling:
        existing = await self.get(tenant_id)
        if existing is not None:
            return existing
        return await self.create_trial(tenant_id, trial_days)

    async def set(self, billing: TenantBilling) -> TenantBilling:
        async with self._lock:
            self._by_tenant[billing.tenant_id] = billing
            return billing

    async def increment_usage(self, tenant_id: str) -> None:
        async with self._lock:
            b = self._by_tenant.get(tenant_id)
            if b is not None:
                b.usage_analises_mes += 1

    async def get_by_subscription_id(self, subscription_id: str) -> TenantBilling | None:
        async with self._lock:
            for b in self._by_tenant.values():
                if b.stripe_subscription_id == subscription_id:
                    return b
            return None

    async def get_by_customer_id(self, customer_id: str) -> TenantBilling | None:
        async with self._lock:
            for b in self._by_tenant.values():
                if b.stripe_customer_id == customer_id:
                    return b
            return None

    async def all(self) -> list[TenantBilling]:
        async with self._lock:
            return list(self._by_tenant.values())
