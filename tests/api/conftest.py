from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

from src.api.deps import get_graph
from src.api.main import create_app
from src.api.store import RunStore
from src.graph.supervisor import build_supervisor


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
