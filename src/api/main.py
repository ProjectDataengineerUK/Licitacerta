from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.admin_audit_store import AdminAuditStore
from src.api.alert_store import AlertStore
from src.api.billing_store import BillingStore
from src.api.feature_flag_store import FeatureFlagStore
from src.api.tenant_state_store import TenantStateStore
from src.api.tenant_user_store import TenantUserStore
from src.api.contract_store import ContractStore
from src.api.pncp_client import PNCPClient
from src.api.routes.admin import router as admin_router
from src.api.routes.market_intel import router as market_intel_router
from src.api.routes.estrategia import router as estrategia_router
from src.api.routes.mentor import router as mentor_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.recebiveis import router as recebiveis_router
from src.api.routes.robo import router as robo_router
from src.api.routes.onboarding import router as onboarding_router
from src.api.routes.sentinela import router as sentinela_router
from src.api.routes.alerts import router as alerts_router
from src.api.routes.config import router as config_router
from src.api.routes.analyze import router as analyze_router
from src.api.routes.billing import router as billing_router
from src.api.routes.certidoes import router as certidoes_router
from src.api.routes.lgpd import router as lgpd_router
from src.api.routes.ativacao import router as ativacao_router
from src.api.routes.proposal_export import router as proposal_export_router
from src.api.routes.outcome import router as outcome_router
from src.api.routes.digest import router as digest_router
from src.api.routes.colaboracao import router as colaboracao_router
from src.api.routes.contracts import router as contracts_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.documents import router as documents_router
from src.api.routes.health_score import router as health_score_router
from src.api.routes.hitl import router as hitl_router
from src.api.routes.radar import router as radar_router
from src.api.routes.runs import router as runs_router
from src.api.routes.tenants import router as tenants_router
from src.api.routes.watch import router as watch_router
from src.api.store import RunStore
from src.api.watch_agent import watch_poll_loop
from src.api.watch_store import WatchStore
from src.config import settings
from src.graph.checkpoint import get_checkpointer
from src.graph.supervisor import build_supervisor


@asynccontextmanager
async def lifespan(app: FastAPI):
    checkpointer, close_checkpointer = await get_checkpointer()
    app.state.graph = build_supervisor(checkpointer=checkpointer)
    app.state.store = RunStore()
    app.state.contract_store = ContractStore()
    app.state.alert_store = AlertStore()
    app.state.billing_store = BillingStore()
    app.state.tenant_user_store = TenantUserStore()
    app.state.watch_store = WatchStore()
    app.state.feature_flag_store = FeatureFlagStore()
    app.state.admin_audit_store = AdminAuditStore()
    app.state.tenant_state_store = TenantStateStore()
    pncp_client = PNCPClient()
    await pncp_client.__aenter__()
    app.state.pncp_client = pncp_client

    # MarketIntelService — inicializa pool asyncpg se DATABASE_URL disponível
    import os as _os
    _db_url = _os.environ.get("DATABASE_URL")
    if _db_url:
        import asyncpg
        from src.services.market_intel_service import MarketIntelService
        _pool = await asyncpg.create_pool(_db_url, min_size=1, max_size=5)
        app.state.market_intel_service = MarketIntelService(_pool)
        app.state._mi_pool = _pool
    else:
        app.state.market_intel_service = None
        app.state._mi_pool = None

    # GCP secret bootstrap — only when running on GCP
    if settings.gcp_project_id:
        from src.gcp.secret_manager import resolve_secrets
        resolve_secrets({
            "ANTHROPIC_API_KEY": f"projects/{settings.gcp_project_id}/secrets/anthropic-api-key/versions/latest",
        })

    interval = int(os.getenv("WATCH_POLL_INTERVAL_SECONDS", "600"))
    _poll_task = asyncio.create_task(
        watch_poll_loop(app.state.watch_store, app.state.store, app.state.graph, interval)
    )
    yield
    _poll_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _poll_task
    await pncp_client.__aexit__(None, None, None)
    if app.state._mi_pool:
        await app.state._mi_pool.close()
    await close_checkpointer()


def create_app() -> FastAPI:
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.middleware.auth import FirebaseAuthMiddleware
    from src.api.middleware.tenant import TenantContextMiddleware

    app = FastAPI(title="LicitaCerta API", version="0.2.0", lifespan=lifespan)

    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from src.api.middleware.admin_auth import AdminAuthMiddleware
    from src.api.middleware.behavior_tracker import BehaviorTrackerMiddleware

    from src.api.middleware.consent import ConsentMiddleware

    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(ConsentMiddleware)
    app.add_middleware(FirebaseAuthMiddleware)
    app.add_middleware(AdminAuthMiddleware)
    app.add_middleware(BehaviorTrackerMiddleware)

    app.include_router(admin_router)
    app.include_router(analyze_router)
    app.include_router(runs_router)
    app.include_router(watch_router)
    app.include_router(documents_router)
    app.include_router(certidoes_router)
    app.include_router(hitl_router)
    app.include_router(tenants_router)
    app.include_router(radar_router)
    app.include_router(dashboard_router)
    app.include_router(contracts_router)
    app.include_router(alerts_router)
    app.include_router(billing_router)
    app.include_router(health_score_router)
    app.include_router(config_router)
    app.include_router(market_intel_router)
    app.include_router(estrategia_router)
    app.include_router(mentor_router)
    app.include_router(portfolio_router)
    app.include_router(recebiveis_router)
    app.include_router(robo_router)
    app.include_router(onboarding_router)
    app.include_router(sentinela_router)
    app.include_router(lgpd_router)
    app.include_router(ativacao_router)
    app.include_router(proposal_export_router)
    app.include_router(outcome_router)
    app.include_router(digest_router)
    app.include_router(colaboracao_router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"ok": True}

    return app


app = create_app()
