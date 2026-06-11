"""PERSISTENCIA_STORES — factory única de stores.

Sem pool (DATABASE_URL ausente): tudo in-memory, comportamento idêntico ao
histórico (dev/CI). Com pool: stores async viram AlloyDB direto; stores sync
ganham write-through (Persister) + hydrate no startup.
"""
from __future__ import annotations

import logging
from typing import Any, NamedTuple

from src.api.admin_audit_store import AdminAuditStore
from src.api.alert_store import AlertStore
from src.api.billing_store import BillingStore
from src.api.contract_store import ContractStore
from src.api.feature_flag_store import FeatureFlagStore
from src.api.store_persistence import Persister
from src.api.tenant_state_store import TenantStateStore
from src.api.tenant_user_store import TenantUserStore
from src.api.watch_store import WatchStore

logger = logging.getLogger(__name__)


class Stores(NamedTuple):
    contracts: Any
    billing: Any
    alerts: Any
    watch: Any
    tenant_users: TenantUserStore
    tenant_states: TenantStateStore
    feature_flags: FeatureFlagStore
    admin_audit: AdminAuditStore
    persister: Persister | None

    async def hydrate(self, pool: Any) -> None:
        """Carrega o estado persistido dos stores sync (write-through)."""
        if pool is None:
            return
        for store in (self.tenant_users, self.tenant_states, self.admin_audit):
            try:
                await store.hydrate(pool)
            except Exception as exc:
                logger.error("hydrate falhou em %s: %s", type(store).__name__, exc)

    async def aclose(self) -> None:
        if self.persister is not None:
            await self.persister.aclose()


def build_stores(pool: Any = None) -> Stores:
    if pool is None:
        return Stores(
            contracts=ContractStore(),
            billing=BillingStore(),
            alerts=AlertStore(),
            watch=WatchStore(),
            tenant_users=TenantUserStore(),
            tenant_states=TenantStateStore(),
            feature_flags=FeatureFlagStore(),
            admin_audit=AdminAuditStore(),
            persister=None,
        )

    from src.api.stores_db import (
        AlloyDBAlertStore,
        AlloyDBBillingStore,
        AlloyDBContractStore,
        AlloyDBWatchStore,
    )

    persister = Persister(pool)
    return Stores(
        contracts=AlloyDBContractStore(pool),
        billing=AlloyDBBillingStore(pool),
        alerts=AlloyDBAlertStore(pool),
        watch=AlloyDBWatchStore(pool),
        tenant_users=TenantUserStore(persister=persister),
        tenant_states=TenantStateStore(persister=persister),
        feature_flags=FeatureFlagStore(),  # COULD do DEFINE — segue in-memory
        admin_audit=AdminAuditStore(persister=persister),
        persister=persister,
    )
