"""AT-001 to AT-006: API key auth + role enforcement tests."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

import src.api.auth as auth_mod
from src.api.deps import get_graph
from src.api.main import create_app
from src.api.store import RunStore
from src.api.watch_store import WatchStore as _WatchStore


def _make_stub_graph():
    from tests.test_pipeline_e2e import (
        _decision_stub,
        _execution_stub,
        _ingestion_stub,
        _post_award_stub,
        _understanding_stub,
        _validation_stub,
    )
    from src.graph.supervisor import build_supervisor

    return build_supervisor(
        ingestion_graph=_ingestion_stub,
        understanding_graph=_understanding_stub,
        validation_graph=_validation_stub,
        decision_graph=_decision_stub,
        execution_graph=_execution_stub,
        post_award_graph=_post_award_stub,
        checkpointer=MemorySaver(),
    )


@pytest_asyncio.fixture()
async def auth_client():
    auth_mod._KEY_STORE = {"op-key": "operator", "usr-key": "user"}
    stub_graph = _make_stub_graph()
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: stub_graph
    app.state.store = RunStore()
    app.state.watch_store = _WatchStore()
    app.state.graph = stub_graph
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    auth_mod._KEY_STORE = {}


def _op():
    return {"Authorization": "Bearer op-key"}


def _usr():
    return {"Authorization": "Bearer usr-key"}


_ANALYZE_BODY = {"edital_raw": "Pregão 001/2026", "cnpj": "12345678000195"}
_APPROVE_BODY = {"approver": "test", "comment": "ok"}
_REJECT_BODY = {"approver": "test", "reason": "no"}


# ---------------------------------------------------------------------------
# Unit tests — parse_api_keys
# ---------------------------------------------------------------------------

def test_parse_api_keys_basic():
    from src.api.auth import parse_api_keys
    result = parse_api_keys("abc:operator,xyz:user")
    assert result == {"abc": "operator", "xyz": "user"}


def test_parse_api_keys_strips_whitespace():
    from src.api.auth import parse_api_keys
    result = parse_api_keys(" abc : operator , xyz : user ")
    assert result == {"abc": "operator", "xyz": "user"}


def test_parse_api_keys_empty():
    from src.api.auth import parse_api_keys
    assert parse_api_keys("") == {}


def test_parse_api_keys_malformed_ignored():
    from src.api.auth import parse_api_keys
    result = parse_api_keys("nocodon,valid:user")
    assert result == {"valid": "user"}


# ---------------------------------------------------------------------------
# AT-001 — 401 sem API key quando auth ativo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at001_401_without_key_analyze(auth_client: AsyncClient):
    resp = await auth_client.post("/analyze", json=_ANALYZE_BODY)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_at001_401_without_key_list_runs(auth_client: AsyncClient):
    resp = await auth_client.get("/runs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_at001_401_invalid_key(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/analyze",
        json=_ANALYZE_BODY,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# AT-002 — 200 com API key válida (user role)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at002_user_can_analyze(auth_client: AsyncClient):
    resp = await auth_client.post("/analyze", json=_ANALYZE_BODY, headers=_usr())
    assert resp.status_code == 202
    assert "run_id" in resp.json()


@pytest.mark.asyncio
async def test_at002_user_can_list_runs(auth_client: AsyncClient):
    resp = await auth_client.get("/runs", headers=_usr())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_at002_operator_can_analyze(auth_client: AsyncClient):
    resp = await auth_client.post("/analyze", json=_ANALYZE_BODY, headers=_op())
    assert resp.status_code == 202


# ---------------------------------------------------------------------------
# AT-003 — 403 com role insuficiente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at003_user_cannot_approve(auth_client: AsyncClient):
    r = await auth_client.post("/analyze", json=_ANALYZE_BODY, headers=_op())
    run_id = r.json()["run_id"]
    resp = await auth_client.post(
        f"/runs/{run_id}/approve", json=_APPROVE_BODY, headers=_usr()
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_at003_user_cannot_reject(auth_client: AsyncClient):
    r = await auth_client.post("/analyze", json=_ANALYZE_BODY, headers=_op())
    run_id = r.json()["run_id"]
    resp = await auth_client.post(
        f"/runs/{run_id}/reject", json=_REJECT_BODY, headers=_usr()
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_at003_user_cannot_create_watch_config(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/watch/configs",
        json={"keywords": ["obra"], "cnpj": "12345678000195"},
        headers=_usr(),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# AT-004 — operator tem acesso total
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at004_operator_approve_not_403(auth_client: AsyncClient):
    r = await auth_client.post("/analyze", json=_ANALYZE_BODY, headers=_op())
    run_id = r.json()["run_id"]
    resp = await auth_client.post(
        f"/runs/{run_id}/approve", json=_APPROVE_BODY, headers=_op()
    )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_at004_operator_can_manage_watch(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/watch/configs",
        json={"keywords": ["pavimentação"], "cnpj": "12345678000195"},
        headers=_op(),
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# AT-005 — /health sempre público
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at005_health_no_auth_needed(auth_client: AsyncClient):
    resp = await auth_client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# AT-006 — dev mode: sem LICITACERTA_API_KEYS → auth desabilitado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at006_dev_mode_no_auth_required(client: AsyncClient):
    # `client` fixture from conftest has _KEY_STORE = {} (dev mode)
    resp = await client.post("/analyze", json=_ANALYZE_BODY)
    assert resp.status_code == 202
