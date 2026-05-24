"""Cloud Run Job: agent pipeline worker.

Triggered after document parsing. Loads parsed JSON from GCS, runs the
LangGraph pipeline (all agents), persists results to AlloyDB, and
publishes a `analysis.completed` or `analysis.hitl_required` event.
"""
from __future__ import annotations

import json
import os


def handle(payload: dict) -> None:
    import asyncio
    asyncio.run(_async_handle(payload))


async def _async_handle(payload: dict) -> None:
    from src.gcp.pubsub import PubSubPublisher
    from src.gcp.storage import GCSDocumentStore
    from src.graph.builder import build_graph

    tenant_id: str = payload["tenant_id"]
    tender_id: str = payload["tender_id"]
    doc_id: str = payload["doc_id"]

    store = GCSDocumentStore.from_env()
    parsed = store.get_parsed(tenant_id, doc_id)

    graph = build_graph()
    initial_state = {
        "tenant_id": tenant_id,
        "tender_id": tender_id,
        "doc_id": doc_id,
        "parsed_pages": parsed.get("pages", []),
        "messages": [],
    }
    result = await graph.ainvoke(initial_state)

    publisher = PubSubPublisher.from_env()
    if result.get("human_decision_required"):
        publisher.publish_event(
            "analysis-hitl-required",
            {"tenant_id": tenant_id, "tender_id": tender_id, "run_id": result.get("run_id", "")},
        )
    else:
        publisher.publish_event(
            "analysis-completed",
            {"tenant_id": tenant_id, "tender_id": tender_id},
        )


if __name__ == "__main__":
    raw = os.environ.get("PAYLOAD_JSON", "{}")
    handle(json.loads(raw))
