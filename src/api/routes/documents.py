"""Document upload route.

POST /documents — multipart upload, stores raw PDF to GCS, enqueues
document ingestion via Cloud Tasks.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(request: Request, file: UploadFile) -> JSONResponse:
    tenant_id: str = getattr(request.state, "tenant_id", "dev")
    doc_id = str(uuid.uuid4())

    content = await file.read()

    from src.gcp.storage import GCSDocumentStore
    from src.gcp.tasks import CloudTasksClient

    store = GCSDocumentStore.from_env()
    gcs_path = store.upload_raw(tenant_id, doc_id, content, file.content_type or "application/pdf")

    tasks = CloudTasksClient.from_env()
    import os
    api_base = os.environ.get("API_BASE_URL", "http://localhost:8000")
    tasks.enqueue_worker(
        queue_name=os.environ.get("TASKS_QUEUE_DOCS", "document-ingestion"),
        payload={"tenant_id": tenant_id, "doc_id": doc_id, "gcs_raw_path": gcs_path},
        url=f"{api_base}/internal/workers/document",
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"doc_id": doc_id, "gcs_path": gcs_path, "status": "processing"},
    )
