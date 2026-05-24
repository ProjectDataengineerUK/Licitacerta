"""Tenant management routes (internal/admin).

POST /internal/tenants  — provision a new tenant
GET  /internal/tenants/{id}  — get tenant info
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/internal/tenants", tags=["tenants"], include_in_schema=False)


class TenantCreate(BaseModel):
    slug: str
    name: str
    cnpj: str
    plan: str = "starter"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(body: TenantCreate) -> JSONResponse:
    tenant_id = str(uuid.uuid4())
    from sqlalchemy import text
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory
    from src.config import settings

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO tenants (id, slug, name, cnpj, plan) "
                "VALUES (:id, :slug, :name, :cnpj, :plan)"
            ),
            {"id": tenant_id, "slug": body.slug, "name": body.name, "cnpj": body.cnpj, "plan": body.plan},
        )
        await session.commit()

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": tenant_id, "slug": body.slug},
    )


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str) -> JSONResponse:
    from sqlalchemy import text
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory
    from src.config import settings

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        row = await session.execute(
            text("SELECT id, slug, name, cnpj, plan, active, created_at FROM tenants WHERE id = :id"),
            {"id": tenant_id},
        )
        result = row.fetchone()

    if result is None:
        return JSONResponse(status_code=404, content={"detail": "Tenant not found"})

    data = {k: str(v) if hasattr(v, "isoformat") else v for k, v in result._mapping.items()}
    return JSONResponse(content=data)
