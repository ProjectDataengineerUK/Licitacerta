from __future__ import annotations
import datetime
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.auth import require_role
from src.services.proposal_exporter import ProposalContent, ProposalExporter, TenantMeta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs/{run_id}/proposal", tags=["proposal-export"])

_PROFISSIONAL_PLANS = {"profissional", "business", "enterprise"}


def _require_profissional(request: Request) -> None:
    plan = getattr(request.state, "plan", "free") or "free"
    if plan not in _PROFISSIONAL_PLANS:
        raise HTTPException(403, "Exportação disponível nos planos Profissional, Business e Enterprise")


def _pool(request: Request):
    return getattr(getattr(request.app, "state", None), "_mi_pool", None)


def _get_store(request: Request):
    return getattr(request.app.state, "store", None)


class ProposalVersionOut(BaseModel):
    id: str
    version_num: int
    formato: str
    gcs_path: str
    criado_em: str


def _extract_content(run) -> ProposalContent | None:
    if not run:
        return None
    snap = run.snapshot or {}
    draft = snap.get("proposal_draft")
    if not draft:
        return None
    if hasattr(draft, "content"):
        content_str, price, validity_days, generated_at = (
            draft.content, draft.price, draft.validity_days, draft.generated_at
        )
    else:
        content_str = draft.get("content", "")
        price = Decimal(str(draft.get("price", "0")))
        validity_days = int(draft.get("validity_days", 60))
        generated_at = datetime.datetime.utcnow()
    return ProposalContent(
        content=content_str,
        price=Decimal(str(price)),
        validity_days=validity_days,
        generated_at=generated_at if isinstance(generated_at, datetime.datetime) else datetime.datetime.utcnow(),
    )


async def _load_tenant_meta(tenant_id: str, pool) -> TenantMeta:
    if not pool:
        return TenantMeta(name="Empresa", cnpj="00.000.000/0000-00")
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT name, cnpj FROM tenants WHERE id=$1", tenant_id
            )
        if row:
            return TenantMeta(name=row["name"] or "Empresa", cnpj=row["cnpj"] or "")
    except Exception as exc:
        logger.warning("proposal_export: tenant meta falhou: %s", exc)
    return TenantMeta(name="Empresa", cnpj="")


async def _save_version(pool, run_id: str, tenant_id: str, formato: str, gcs_path: str) -> int:
    async with pool.acquire() as conn:
        async with conn.transaction():
            version_num = await conn.fetchval(
                """SELECT COALESCE(MAX(version_num), 0) + 1
                   FROM proposal_versions
                   WHERE run_id=$1 AND formato=$2
                   FOR UPDATE""",
                run_id,
                formato,
            )
            await conn.execute(
                """INSERT INTO proposal_versions (run_id, tenant_id, version_num, formato, gcs_path)
                   VALUES ($1,$2,$3,$4,$5)""",
                run_id,
                tenant_id,
                version_num,
                formato,
                gcs_path,
            )
    return version_num


def _gcs_upload(tenant_id: str, run_id: str, version_num: int, ext: str, data: bytes, content_type: str) -> str:
    try:
        import os
        from google.cloud import storage

        bucket_name = os.environ.get("GCS_BUCKET_DOCS")
        if not bucket_name:
            return f"local://{tenant_id}/{run_id}/v{version_num}.{ext}"
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob_path = f"proposals/{tenant_id}/{run_id}/v{version_num}.{ext}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{bucket_name}/{blob_path}"
    except Exception as exc:
        logger.warning("proposal_export: gcs upload falhou: %s", exc)
        return f"local://{tenant_id}/{run_id}/v{version_num}.{ext}"


@router.post("/export")
async def export_proposal(
    run_id: str,
    request: Request,
    format: str = "docx",
    vertical: str = "geral",
    _auth=Depends(require_role("user", "operator")),
    _plan_check=Depends(_require_profissional),
):
    if format not in ("docx", "pdf"):
        raise HTTPException(400, "format deve ser 'docx' ou 'pdf'")
    if vertical not in ("geral", "ti", "limpeza", "obras"):
        raise HTTPException(400, "vertical inválida")

    tenant_id = getattr(request.state, "tenant_id", "") or ""
    store = _get_store(request)
    run = store.get_run(run_id) if store else None
    proposal_content = _extract_content(run)
    if proposal_content is None:
        raise HTTPException(409, "Run não possui proposta gerada")

    pool = _pool(request)
    tenant = await _load_tenant_meta(tenant_id, pool)
    exporter = ProposalExporter()

    if format == "docx":
        try:
            buf = exporter.render_docx(proposal_content, vertical, tenant)  # type: ignore[arg-type]
            data = buf.read()
        except Exception as exc:
            logger.warning("proposal_export: docx falhou: %s", exc)
            raise HTTPException(500, "Falha ao gerar DOCX") from exc
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        try:
            data = exporter.render_pdf(proposal_content, vertical, tenant)  # type: ignore[arg-type]
        except Exception as exc:
            logger.warning("proposal_export: pdf falhou: %s", exc)
            raise HTTPException(500, "Falha ao gerar PDF") from exc
        content_type = "application/pdf"

    version_num = 1
    if pool:
        try:
            gcs_path = _gcs_upload(tenant_id, run_id, 999, format, data, content_type)
            version_num = await _save_version(pool, run_id, tenant_id, format, gcs_path)
            gcs_path = _gcs_upload(tenant_id, run_id, version_num, format, data, content_type)
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE proposal_versions SET gcs_path=$1 WHERE run_id=$2 AND version_num=$3 AND formato=$4",
                    gcs_path, run_id, version_num, format,
                )
        except Exception as exc:
            logger.warning("proposal_export: versioning falhou: %s", exc)

    return StreamingResponse(
        iter([data]),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="proposta_v{version_num}.{format}"'},
    )


@router.get("/versions", response_model=list[ProposalVersionOut])
async def list_versions(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, version_num, formato, gcs_path, criado_em
               FROM proposal_versions
               WHERE run_id=$1 AND tenant_id=$2
               ORDER BY version_num ASC""",
            run_id,
            tenant_id,
        )
    return [
        ProposalVersionOut(
            id=str(r["id"]),
            version_num=r["version_num"],
            formato=r["formato"],
            gcs_path=r["gcs_path"],
            criado_em=r["criado_em"].isoformat(),
        )
        for r in rows
    ]


@router.get("/versions/{version_id}/download")
async def download_version(
    run_id: str,
    version_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    if not pool:
        raise HTTPException(503, "Banco indisponível")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT formato, gcs_path FROM proposal_versions WHERE id=$1 AND tenant_id=$2",
            version_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(404, "Versão não encontrada")
    try:
        from src.gcp.storage import GCSDocumentStore
        store = GCSDocumentStore.from_env()
        data = store.download_raw(row["gcs_path"])
    except Exception as exc:
        raise HTTPException(503, "Falha ao baixar arquivo") from exc
    ct = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if row["formato"] == "docx"
        else "application/pdf"
    )
    return StreamingResponse(
        iter([data]),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="proposta.{row["formato"]}"'},
    )


@router.get("/preview")
async def preview_proposal(
    run_id: str,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    store = _get_store(request)
    run = store.get_run(run_id) if store else None
    proposal_content = _extract_content(run)
    if proposal_content is None:
        raise HTTPException(409, "Run não possui proposta gerada")
    tenant_id = getattr(request.state, "tenant_id", "") or ""
    pool = _pool(request)
    tenant = await _load_tenant_meta(tenant_id, pool)
    exporter = ProposalExporter()
    html = exporter.render_html_preview(proposal_content, tenant)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
