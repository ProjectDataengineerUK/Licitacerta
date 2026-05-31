from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.alert_store import AlertStore
from src.api.contract_store import ContractStore
from src.api.pncp_client import PNCPClient
from src.api.routes.alerts import router as alerts_router
from src.api.routes.analyze import router as analyze_router
from src.api.routes.certidoes import router as certidoes_router
from src.api.routes.contracts import router as contracts_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.documents import router as documents_router
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
    app.state.watch_store = WatchStore()
    pncp_client = PNCPClient()
    await pncp_client.__aenter__()
    app.state.pncp_client = pncp_client

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
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(FirebaseAuthMiddleware)

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

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"ok": True}

    return app


app = create_app()
