from __future__ import annotations

from fastapi import Request

from src.api.alert_store import AlertStore
from src.api.billing_store import BillingStore
from src.api.contract_store import ContractStore
from src.api.pncp_client import PNCPClient
from src.api.store import RunStore
from src.api.tenant_user_store import TenantUserStore
from src.api.watch_store import WatchStore


def get_store(request: Request) -> RunStore:
    return request.app.state.store


def get_contract_store(request: Request) -> ContractStore:
    return request.app.state.contract_store


def get_alert_store(request: Request) -> AlertStore:
    return request.app.state.alert_store


def get_billing_store(request: Request) -> BillingStore:
    return request.app.state.billing_store


def get_reajuste_service():
    from src.services.reajuste import ReajusteService

    return ReajusteService()


def get_graph(request: Request):
    return request.app.state.graph


def get_watch_store(request: Request) -> WatchStore:
    return request.app.state.watch_store


def get_pncp_client(request: Request) -> PNCPClient:
    return request.app.state.pncp_client


def get_tenant_user_store(request: Request) -> TenantUserStore:
    return request.app.state.tenant_user_store
