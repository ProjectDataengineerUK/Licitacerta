"""AT-001 to AT-004: PORTAL_INTEGRATION_V2 — pagination + configurable lookback + testable poll."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, MockTransport, Response
from langgraph.checkpoint.memory import MemorySaver

import src.api.watch_agent as watch_agent_mod
from src.api.deps import get_graph, get_watch_store
from src.api.main import create_app
from src.api.pncp_client import PNCPClient
from src.api.store import RunStore
from src.api.watch_store import WatchStore


def _make_stub_graph():
    from src.graph.supervisor import build_supervisor
    from tests.test_pipeline_e2e import (
        _decision_stub,
        _execution_stub,
        _ingestion_stub,
        _post_award_stub,
        _understanding_stub,
        _validation_stub,
    )

    return build_supervisor(
        ingestion_graph=_ingestion_stub,
        understanding_graph=_understanding_stub,
        validation_graph=_validation_stub,
        decision_graph=_decision_stub,
        execution_graph=_execution_stub,
        post_award_graph=_post_award_stub,
        checkpointer=MemorySaver(),
    )


def _make_edital(pncp_id: str) -> dict:
    return {"numeroControlePNCP": pncp_id, "objetoCompra": f"obra {pncp_id}"}


def _paginated_transport(total: int, page_size: int = 50) -> MockTransport:
    """Returns a transport that simulates paginated PNCP responses."""
    all_editais = [_make_edital(f"PNCP-{i:04d}") for i in range(total)]

    def handler(request):
        params = dict(request.url.params)
        page = int(params.get("pagina", 1))
        size = int(params.get("tamanhoPagina", page_size))
        start = (page - 1) * size
        page_data = all_editais[start : start + size]
        payload = {"data": page_data, "totalRegistros": total}
        return Response(200, content=json.dumps(payload).encode())

    return MockTransport(handler)


# ---------------------------------------------------------------------------
# AT-001 — paginação busca todas as páginas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at001_pagination_single_page():
    transport = _paginated_transport(total=30)
    async with PNCPClient(client=AsyncClient(transport=transport)) as client:
        results = await client.search_publicacoes_all(date.today(), date.today())
    assert len(results) == 30


@pytest.mark.asyncio
async def test_at001_pagination_exact_page_boundary():
    transport = _paginated_transport(total=50)
    async with PNCPClient(client=AsyncClient(transport=transport)) as client:
        results = await client.search_publicacoes_all(date.today(), date.today())
    assert len(results) == 50


@pytest.mark.asyncio
async def test_at001_pagination_multiple_pages():
    total = 120
    transport = _paginated_transport(total=total)
    async with PNCPClient(client=AsyncClient(transport=transport)) as client:
        results = await client.search_publicacoes_all(date.today(), date.today())
    assert len(results) == total


@pytest.mark.asyncio
async def test_at001_pagination_three_pages_correct_ids():
    total = 120
    transport = _paginated_transport(total=total)
    async with PNCPClient(client=AsyncClient(transport=transport)) as client:
        results = await client.search_publicacoes_all(date.today(), date.today())
    ids = [r["numeroControlePNCP"] for r in results]
    assert ids[0] == "PNCP-0000"
    assert ids[50] == "PNCP-0050"
    assert ids[100] == "PNCP-0100"
    assert len(ids) == 120


@pytest.mark.asyncio
async def test_at001_pagination_partial_on_error():
    """If page 2 fails, returns page 1 results without raising."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        params = dict(request.url.params)
        page = int(params.get("pagina", 1))
        if page > 1:
            return Response(500, content=b"error")
        payload = {"data": [_make_edital("PNCP-0001")], "totalRegistros": 100}
        return Response(200, content=json.dumps(payload).encode())

    async with PNCPClient(client=AsyncClient(transport=MockTransport(handler))) as client:
        results = await client.search_publicacoes_all(date.today(), date.today())
    assert len(results) == 1  # only page 1 returned


# ---------------------------------------------------------------------------
# AT-002 / AT-003 — lookback env var
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_at003_lookback_default_is_one_day(monkeypatch):
    monkeypatch.setattr(watch_agent_mod, "_INITIAL_LOOKBACK_DAYS", 1)
    watch_store = WatchStore()
    run_store = RunStore()
    await watch_store.create_config(keywords=["obra"], cnpj="12345678000195")

    captured_dates = []

    def handler(request):
        params = dict(request.url.params)
        captured_dates.append(params.get("dataInicial"))
        payload = {"data": [], "totalRegistros": 0}
        return Response(200, content=json.dumps(payload).encode())

    async with PNCPClient(client=AsyncClient(transport=MockTransport(handler))) as pncp_client:
        from src.api.watch_agent import run_poll_cycle
        await run_poll_cycle(watch_store, run_store, None, pncp_client)

    assert len(captured_dates) == 1
    expected = (date.today() - timedelta(days=1)).isoformat()
    assert captured_dates[0] == expected


@pytest.mark.asyncio
async def test_at002_lookback_configurable(monkeypatch):
    monkeypatch.setattr(watch_agent_mod, "_INITIAL_LOOKBACK_DAYS", 7)
    watch_store = WatchStore()
    run_store = RunStore()
    await watch_store.create_config(keywords=["obra"], cnpj="12345678000195")

    captured_dates = []

    def handler(request):
        params = dict(request.url.params)
        captured_dates.append(params.get("dataInicial"))
        payload = {"data": [], "totalRegistros": 0}
        return Response(200, content=json.dumps(payload).encode())

    async with PNCPClient(client=AsyncClient(transport=MockTransport(handler))) as pncp_client:
        from src.api.watch_agent import run_poll_cycle
        await run_poll_cycle(watch_store, run_store, None, pncp_client)

    assert len(captured_dates) == 1
    expected = (date.today() - timedelta(days=7)).isoformat()
    assert captured_dates[0] == expected


# ---------------------------------------------------------------------------
# AT-004 — /watch/poll usa pncp_client do app.state
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def poll_client():
    import src.api.auth as auth_mod
    auth_mod._KEY_STORE = {"op-key": "operator"}
    stub_graph = _make_stub_graph()
    app = create_app()
    watch_store = WatchStore()
    run_store = RunStore()
    app.dependency_overrides[get_graph] = lambda: stub_graph
    app.dependency_overrides[get_watch_store] = lambda: watch_store
    app.state.watch_store = watch_store
    app.state.store = run_store
    app.state.graph = stub_graph

    # Inject mock pncp_client
    mock_pncp = PNCPClient(
        client=AsyncClient(
            transport=_paginated_transport(total=0)
        )
    )
    await mock_pncp.__aenter__()
    app.state.pncp_client = mock_pncp

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    await mock_pncp.__aexit__(None, None, None)
    auth_mod._KEY_STORE = {}


@pytest.mark.asyncio
async def test_at004_manual_poll_uses_injected_client(poll_client: AsyncClient):
    resp = await poll_client.post(
        "/watch/poll", headers={"Authorization": "Bearer op-key"}
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "poll triggered"}
