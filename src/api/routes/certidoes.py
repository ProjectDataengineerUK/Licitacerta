"""Certidões (tax/regulatory certificates) routes.

GET  /certidoes        — list tenant's certificates
POST /certidoes        — upload a new certificate
GET  /certidoes/{id}   — get single certificate metadata
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/certidoes", tags=["certidoes"])


@router.get("")
async def list_certidoes(request: Request) -> JSONResponse:
    tenant_id: str = getattr(request.state, "tenant_id", "dev")
    from sqlalchemy import text

    from src.config import settings
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory, tenant_session

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with tenant_session(session_factory, tenant_id) as session:
        rows = await session.execute(
            text("SELECT id, tipo, status, valid_until, gcs_path, created_at FROM certidoes ORDER BY created_at DESC")
        )
        items = [dict(r._mapping) for r in rows.fetchall()]

    return JSONResponse(content={"certidoes": [_serialize(i) for i in items]})


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_certidao(request: Request, file: UploadFile, tipo: str) -> JSONResponse:
    tenant_id: str = getattr(request.state, "tenant_id", "dev")
    cert_id = str(uuid.uuid4())

    content = await file.read()
    from src.gcp.storage import GCSDocumentStore
    store = GCSDocumentStore.from_env()
    gcs_path = store.upload_raw(tenant_id, f"cert_{cert_id}", content, file.content_type or "application/pdf")

    from sqlalchemy import text

    from src.config import settings
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory, tenant_session

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with tenant_session(session_factory, tenant_id) as session:
        await session.execute(
            text(
                "INSERT INTO certidoes (id, tenant_id, tipo, status, gcs_path) "
                "VALUES (:id, :tenant_id, :tipo, 'pending_review', :gcs_path)"
            ),
            {"id": cert_id, "tenant_id": tenant_id, "tipo": tipo, "gcs_path": gcs_path},
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"id": cert_id, "gcs_path": gcs_path, "status": "pending_review"},
    )


def _serialize(row: dict) -> dict:
    return {k: str(v) if hasattr(v, "isoformat") else v for k, v in row.items()}
