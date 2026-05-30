from __future__ import annotations

import functools
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text

from src.api.auth import require_role
from src.config import settings

router = APIRouter(prefix="/radar", tags=["radar"])


@functools.lru_cache(maxsize=1)
def _get_sf():
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory
    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    return create_session_factory(engine)


def _tid(request: Request) -> str:
    return getattr(request.state, "tenant_id", "dev")


class PredictionResponse(BaseModel):
    id: str
    orgao_nome: str | None
    objeto_previsto: str | None
    valor_estimado_brl: float | None
    data_prevista_publicacao: str
    confianca_pct: float
    fonte: str
    dias_antecedencia: int
    status: str


def _row_to_resp(r) -> PredictionResponse:
    dias = r.dias_ant.days if r.dias_ant else 0
    return PredictionResponse(
        id=str(r.id),
        orgao_nome=r.orgao_nome,
        objeto_previsto=r.objeto_previsto,
        valor_estimado_brl=float(r.valor_estimado_brl) if r.valor_estimado_brl else None,
        data_prevista_publicacao=r.data_prevista_publicacao.isoformat(),
        confianca_pct=r.confianca_pct,
        fonte=r.fonte,
        dias_antecedencia=int(dias),
        status=r.status,
    )


@router.get("/predictions", response_model=list[PredictionResponse])
async def list_predictions(
    request: Request,
    min_confianca: float = Query(default=50.0, ge=0, le=100),
    _auth=Depends(require_role("user", "operator")),
):
    tid = _tid(request)
    try:
        async with _get_sf()() as session:
            await session.execute(text("SET LOCAL app.current_tenant_id = :t"), {"t": tid})
            rows = await session.execute(
                text("""
                    SELECT id, orgao_nome, objeto_previsto, valor_estimado_brl,
                           data_prevista_publicacao, confianca_pct, fonte, status,
                           (data_prevista_publicacao - CURRENT_DATE) AS dias_ant
                    FROM procurement_predictions
                    WHERE tenant_id::text = :tid
                      AND confianca_pct >= :mc AND status != 'cancelado'
                    ORDER BY confianca_pct DESC LIMIT 50
                """),
                {"tid": tid, "mc": min_confianca},
            )
            return [_row_to_resp(r) for r in rows.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: UUID,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    tid = _tid(request)
    try:
        async with _get_sf()() as session:
            await session.execute(text("SET LOCAL app.current_tenant_id = :t"), {"t": tid})
            row = (await session.execute(
                text("""
                    SELECT id, orgao_nome, objeto_previsto, valor_estimado_brl,
                           data_prevista_publicacao, confianca_pct, fonte, status,
                           (data_prevista_publicacao - CURRENT_DATE) AS dias_ant
                    FROM procurement_predictions
                    WHERE id = :pid AND tenant_id::text = :tid
                """),
                {"pid": str(prediction_id), "tid": tid},
            )).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    if not row:
        raise HTTPException(status_code=404, detail="prediction not found")
    return _row_to_resp(row)


@router.post("/predictions/{prediction_id}/dismiss", status_code=204)
async def dismiss_prediction(
    prediction_id: UUID,
    request: Request,
    _auth=Depends(require_role("user", "operator")),
):
    tid = _tid(request)
    try:
        async with _get_sf()() as session:
            await session.execute(text("SET LOCAL app.current_tenant_id = :t"), {"t": tid})
            await session.execute(
                text("UPDATE procurement_predictions SET status='cancelado' WHERE id=:id AND tenant_id::text = :tid"),
                {"id": str(prediction_id), "tid": tid},
            )
            await session.commit()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
