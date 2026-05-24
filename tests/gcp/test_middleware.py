"""Unit tests for auth and tenant middleware — no Firebase calls."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _make_app_with_middleware():
    from src.api.middleware.auth import FirebaseAuthMiddleware
    from src.api.middleware.tenant import TenantContextMiddleware, current_tenant_id

    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(FirebaseAuthMiddleware)

    @app.get("/me")
    async def me(request: Request):
        return {
            "uid": getattr(request.state, "uid", None),
            "tenant_id": getattr(request.state, "tenant_id", None),
            "ctx_tenant": current_tenant_id.get(),
        }

    return app


@pytest_asyncio.fixture
async def client():
    app = _make_app_with_middleware()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_no_gcp_project_bypasses_auth(client):
    # GCP_PROJECT_ID not set → bypass, use header
    resp = await client.get("/me", headers={"X-Tenant-Id": "tenant-abc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["uid"] == "local-dev"
    assert data["tenant_id"] == "tenant-abc"
    assert data["ctx_tenant"] == "tenant-abc"


@pytest.mark.asyncio
async def test_missing_bearer_returns_401(monkeypatch, client):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    resp = await client.get("/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_healthz_bypasses_auth(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    app = _make_app_with_middleware()

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    assert resp.status_code == 200
