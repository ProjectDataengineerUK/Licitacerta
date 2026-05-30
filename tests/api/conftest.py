from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

from src.api.deps import get_graph
from src.api.main import create_app
from src.api.store import RunStore
from src.graph.supervisor import build_supervisor


@pytest.fixture(autouse=True)
def _fast_queue_cleanup(monkeypatch):
    """Avoid RunStore cleanup tasks sleeping 300s and leaking past the test."""
    monkeypatch.setenv("QUEUE_CLEANUP_DELAY_SECONDS", "0.01")


@pytest_asyncio.fixture(autouse=True)
async def _drain_pending_tasks():
    """Cancel and await leftover background tasks so their coroutines unwind in
    this test's event loop. Otherwise fire-and-forget tasks (e.g. the /analyze
    ``_run`` graph executions and RunStore cleanup) get garbage-collected at
    nondeterministic times during *later* tests, raising ``GeneratorExit`` /
    unraisable warnings that flakily break unrelated async tests (e.g. respx
    mocks in test_pncp_pca)."""
    yield
    pending = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and not t.done()
    ]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


def _make_stub_graph():
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


@pytest_asyncio.fixture()
async def client():
    stub_graph = _make_stub_graph()
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: stub_graph
    app.state.store = RunStore()
    app.state.graph = stub_graph

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
