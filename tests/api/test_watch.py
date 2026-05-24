"""AT-001 to AT-005: Watch Agent PNCP tests."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, MockTransport, Response
from langgraph.checkpoint.memory import MemorySaver

from src.api.deps import get_watch_store
from src.api.main import create_app
from src.api.pncp_client import PNCPClient
from src.api.store import RunStore
from src.api.watch_agent import _matches, run_poll_cycle
from src.api.watch_store import WatchStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _pncp_transport(editais: list[dict]) -> MockTransport:
    import json

    def handler(request):
        return Response(200, content=json.dumps({"data": editais, "totalRegistros": len(editais)}).encode())

    return MockTransport(handler)


def _pncp_error_transport() -> MockTransport:
    def handler(request):
        return Response(500, content=b"Internal Server Error")

    return MockTransport(handler)


def _make_edital(pncp_id: str, objeto: str) -> dict:
    return {"numeroControlePNCP": pncp_id, "objetoCompra": objeto}


@pytest_asyncio.fixture()
async def watch_client():
    stub_graph = _make_stub_graph()
    app = create_app()
    watch_store = WatchStore()
    run_store = RunStore()
    app.dependency_overrides[get_watch_store] = lambda: watch_store
    app.state.watch_store = watch_store
    app.state.store = run_store
    app.state.graph = stub_graph

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Unit — _matches
# ---------------------------------------------------------------------------

def test_matches_keyword_found():
    edital = _make_edital("X", "Pregão para aquisição de papel A4 e materiais de escritório")
    assert _matches(edital, ["papel a4"])


def test_matches_case_insensitive():
    edital = _make_edital("X", "Construção civil de passarela")
    assert _matches(edital, ["CONSTRUÇÃO CIVIL"])


def test_matches_no_match():
    edital = _make_edital("X", "Serviços de limpeza predial")
    assert not _matches(edital, ["construção civil", "reforma"])


def test_matches_empty_keywords():
    edital = _make_edital("X", "Qualquer coisa")
    assert not _matches(edital, [])


def test_matches_missing_objeto():
    edital = {"numeroControlePNCP": "X"}
    assert not _matches(edital, ["construção"])


# ---------------------------------------------------------------------------
# Unit — WatchStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watch_store_create_and_list():
    store = WatchStore()
    cfg = await store.create_config(keywords=["obra", "reforma"], cnpj="12345678000195")
    configs = await store.list_configs()
    assert len(configs) == 1
    assert configs[0].id == cfg.id
    assert configs[0].cnpj == "12345678000195"


@pytest.mark.asyncio
async def test_watch_store_delete():
    store = WatchStore()
    cfg = await store.create_config(keywords=["obra"], cnpj="12345678000195")
    deleted = await store.delete_config(cfg.id)
    assert deleted is True
    assert await store.list_configs() == []


@pytest.mark.asyncio
async def test_watch_store_delete_nonexistent():
    from uuid import uuid4
    store = WatchStore()
    assert await store.delete_config(uuid4()) is False


@pytest.mark.asyncio
async def test_watch_store_is_seen_and_record():
    store = WatchStore()
    cfg = await store.create_config(keywords=["obra"], cnpj="12345678000195")
    assert not await store.is_seen("PNCP-001")
    await store.record("PNCP-001", cfg.id, "run-abc")
    assert await store.is_seen("PNCP-001")


# ---------------------------------------------------------------------------
# Unit — run_poll_cycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_at001_new_edital_triggers_analyze():
    """AT-001: novo edital com keyword dispara _trigger_analyze."""
    watch_store = WatchStore()
    run_store = RunStore()
    stub_graph = _make_stub_graph()
    await watch_store.create_config(keywords=["construção civil"], cnpj="12345678000195")

    editais = [_make_edital("PNCP-2026-001", "Construção civil de passarela urbana")]
    pncp_client = PNCPClient(client=AsyncClient(transport=_pncp_transport(editais)))

    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)

    assert await watch_store.is_seen("PNCP-2026-001")
    runs = await run_store.list_all()
    assert len(runs) == 1
    assert runs[0].edital_id == "PNCP-2026-001"


@pytest.mark.asyncio
async def test_at002_duplicate_pncp_id_not_triggered():
    """AT-002: edital já visto não dispara segundo run."""
    watch_store = WatchStore()
    run_store = RunStore()
    stub_graph = _make_stub_graph()
    await watch_store.create_config(keywords=["construção"], cnpj="12345678000195")

    editais = [_make_edital("PNCP-2026-DUP", "Construção de muro")]
    pncp_client = PNCPClient(client=AsyncClient(transport=_pncp_transport(editais)))

    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)
    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)

    runs = await run_store.list_all()
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_at003_inactive_config_skipped():
    """AT-003: WatchConfig inativa não dispara poll."""
    watch_store = WatchStore()
    run_store = RunStore()
    stub_graph = _make_stub_graph()
    cfg = await watch_store.create_config(keywords=["construção"], cnpj="12345678000195")
    cfg.active = False

    editais = [_make_edital("PNCP-2026-SKIP", "Construção de passarela")]
    pncp_client = PNCPClient(client=AsyncClient(transport=_pncp_transport(editais)))

    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)

    assert not await watch_store.is_seen("PNCP-2026-SKIP")
    assert await run_store.list_all() == []


@pytest.mark.asyncio
async def test_at004_pncp_error_resilience():
    """AT-004: erro HTTP no PNCP não quebra o ciclo."""
    watch_store = WatchStore()
    run_store = RunStore()
    stub_graph = _make_stub_graph()
    await watch_store.create_config(keywords=["obra"], cnpj="12345678000195")

    pncp_client = PNCPClient(client=AsyncClient(transport=_pncp_error_transport()))

    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)

    assert await run_store.list_all() == []


@pytest.mark.asyncio
async def test_poll_only_matches_keyword():
    """Edital sem keyword não dispara run."""
    watch_store = WatchStore()
    run_store = RunStore()
    stub_graph = _make_stub_graph()
    await watch_store.create_config(keywords=["construção civil"], cnpj="12345678000195")

    editais = [_make_edital("PNCP-2026-X", "Serviços de vigilância patrimonial")]
    pncp_client = PNCPClient(client=AsyncClient(transport=_pncp_transport(editais)))

    await run_poll_cycle(watch_store, run_store, stub_graph, pncp_client)

    assert not await watch_store.is_seen("PNCP-2026-X")
    assert await run_store.list_all() == []


# ---------------------------------------------------------------------------
# Integration — REST endpoints (AT-005)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_at005_create_watch_config(watch_client: AsyncClient):
    resp = await watch_client.post(
        "/watch/configs",
        json={"keywords": ["construção civil"], "cnpj": "12345678000195"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["cnpj"] == "12345678000195"
    assert body["keywords"] == ["construção civil"]
    assert "id" in body


@pytest.mark.asyncio
async def test_at005_list_watch_configs(watch_client: AsyncClient):
    await watch_client.post(
        "/watch/configs",
        json={"keywords": ["reforma"], "cnpj": "12345678000195"},
    )
    resp = await watch_client.get("/watch/configs")
    assert resp.status_code == 200
    configs = resp.json()
    assert len(configs) == 1
    assert configs[0]["keywords"] == ["reforma"]


@pytest.mark.asyncio
async def test_at005_delete_watch_config(watch_client: AsyncClient):
    create_resp = await watch_client.post(
        "/watch/configs",
        json={"keywords": ["obra"], "cnpj": "12345678000195"},
    )
    config_id = create_resp.json()["id"]

    del_resp = await watch_client.delete(f"/watch/configs/{config_id}")
    assert del_resp.status_code == 204

    list_resp = await watch_client.get("/watch/configs")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_at005_delete_nonexistent_returns_404(watch_client: AsyncClient):
    from uuid import uuid4
    resp = await watch_client.delete(f"/watch/configs/{uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_at005_create_requires_keywords_and_cnpj(watch_client: AsyncClient):
    resp = await watch_client.post("/watch/configs", json={"keywords": ["obra"]})
    assert resp.status_code == 422

    resp = await watch_client.post("/watch/configs", json={"cnpj": "12345678000195"})
    assert resp.status_code == 422
