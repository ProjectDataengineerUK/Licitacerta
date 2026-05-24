"""Cloud Run Job: document ingestion worker.

Triggered by Cloud Tasks or Pub/Sub. Reads a PDF from GCS (raw tier),
runs Document AI OCR, saves parsed JSON to GCS (parsed tier), and
publishes a `document.parsed` event to Pub/Sub.
"""
from __future__ import annotations

import json
import os

from src.config import settings
from src.gcp.document_ai import DocumentAIClient
from src.gcp.pubsub import PubSubPublisher
from src.gcp.storage import GCSDocumentStore


def handle(payload: dict) -> None:
    tenant_id: str = payload["tenant_id"]
    doc_id: str = payload["doc_id"]

    store = GCSDocumentStore.from_env()
    dai = DocumentAIClient.from_env()
    publisher = PubSubPublisher.from_env()

    raw_path = payload.get("gcs_raw_path") or f"raw/{tenant_id}/{doc_id}.pdf"
    content = store.download_raw(raw_path)

    pages = dai.process_pdf(content)
    parsed = {"doc_id": doc_id, "pages": [p.model_dump() for p in pages]}
    gcs_parsed_path = store.save_parsed(tenant_id, doc_id, parsed)

    publisher.publish_event(
        "document-parsed",
        {"tenant_id": tenant_id, "doc_id": doc_id, "gcs_parsed_path": gcs_parsed_path},
    )


if __name__ == "__main__":
    raw = os.environ.get("PAYLOAD_JSON", "{}")
    handle(json.loads(raw))
