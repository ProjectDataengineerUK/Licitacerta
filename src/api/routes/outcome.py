from __future__ import annotations
import csv
import io
import json
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

router = APIRouter(tags=["outcome"])

_PROFISSIONAL_PLANS = {"profissional", "business", "enterprise"}


def _plan(request: Request) -> str:
    return getattr(request.state, "plan", "free") or "free"


def _pool(request: Request):
    return getattr(getattr(request.app, "state", None), "_mi_pool", None)


def _store(request: Request):
    return getattr(request.app.state, "store", None)


class OutcomeIn(BaseModel):
    resultado: Literal["ganhou", "perdeu", "desistiu"]
    preco_vencedor: Decimal | None = None
    preco_proposto: Decimal | None = None
    observacao: str | None = None


@router.post("/runs/{run_id}/outcome", status_code=201)
async def create_outcome(run_id: str, body: OutcomeIn, request: Request):
    from src.services.outcome_learner import gerar_insight

    pool = _pool(request)
    store = _store(request)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(401, "tenant não identificado")
    if not pool:
        raise HTTPException(503, "Banco indisponível")

    run = store.get_run(run_id) if store else None
    snap = {}
    score = None
    if run:
        snap = run.snapshot or {}
        bid = snap.get("bid_decision") or {}
        score = bid.get("confidence")

    insight = await gerar_insight(
        score=float(score) if score is not None else None,
        resultado=body.resultado,
        preco_proposto=float(body.preco_proposto) if body.preco_proposto else None,
        preco_vencedor=float(body.preco_vencedor) if body.preco_vencedor else None,
    )

    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO run_outcomes (
                run_id, tenant_id, resultado, preco_vencedor, preco_proposto,
                observacao, outcome_insight, segmento, uf, modalidade,
                faixa_valor, bid_no_bid_score
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (run_id) DO UPDATE SET
                resultado=EXCLUDED.resultado,
                preco_vencedor=EXCLUDED.preco_vencedor,
                preco_proposto=EXCLUDED.preco_proposto,
                observacao=EXCLUDED.observacao,
                outcome_insight=EXCLUDED.outcome_insight,
                registrado_em=NOW()""",
            run_id,
            tenant_id,
            body.resultado,
            body.preco_vencedor,
            body.preco_proposto,
            body.observacao,
            insight,
            snap.get("segmento"),
            snap.get("uf"),
            snap.get("modalidade"),
            snap.get("faixa_valor"),
            score,
        )
    return {"run_id": run_id, "insight": insight}


@router.get("/runs/{run_id}/outcome")
async def get_outcome(run_id: str, request: Request):
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not pool:
        raise HTTPException(503, "Banco indisponível")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM run_outcomes WHERE run_id=$1 AND tenant_id=$2",
            run_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(404)
    return dict(row)


@router.get("/historico")
async def list_historico(request: Request, page: int = 1, page_size: int = 20):
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", None)
    plan = _plan(request)
    is_limited = plan not in _PROFISSIONAL_PLANS
    limit = 3 if is_limited else page_size
    offset = 0 if is_limited else (page - 1) * page_size

    if not pool:
        raise HTTPException(503, "Banco indisponível")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM run_outcomes
               WHERE tenant_id=$1
               ORDER BY registrado_em DESC
               LIMIT $2 OFFSET $3""",
            tenant_id,
            limit,
            offset,
        )

    headers = {"X-Plan-Limited": "true"} if is_limited else {}
    return Response(
        content=json.dumps([dict(r) for r in rows], default=str),
        media_type="application/json",
        headers=headers,
    )


@router.get("/historico/stats")
async def historico_stats(request: Request):
    plan = _plan(request)
    if plan not in _PROFISSIONAL_PLANS:
        raise HTTPException(403, "Disponível nos planos Profissional, Business e Enterprise")
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not pool:
        raise HTTPException(503, "Banco indisponível")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT
                GROUPING(segmento) AS g_seg,
                GROUPING(uf) AS g_uf,
                GROUPING(modalidade) AS g_mod,
                segmento, uf, modalidade,
                COUNT(*) AS total,
                SUM(CASE WHEN resultado='ganhou' THEN 1 ELSE 0 END) AS ganhou,
                AVG(bid_no_bid_score) AS avg_score
            FROM run_outcomes
            WHERE tenant_id=$1
            GROUP BY GROUPING SETS (
                (segmento), (uf), (modalidade), ()
            )""",
            tenant_id,
        )
    return [dict(r) for r in rows]


@router.get("/historico/export")
async def export_csv(request: Request):
    plan = _plan(request)
    if plan not in _PROFISSIONAL_PLANS:
        raise HTTPException(403, "Disponível nos planos Profissional, Business e Enterprise")
    pool = _pool(request)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not pool:
        raise HTTPException(503, "Banco indisponível")

    async def generate():
        buf = io.StringIO()
        writer = None
        async with pool.acquire() as conn:
            async with conn.transaction():
                async for row in conn.cursor(
                    "SELECT * FROM run_outcomes WHERE tenant_id=$1 ORDER BY registrado_em DESC",
                    tenant_id,
                    prefetch=100,
                ):
                    d = dict(row)
                    if writer is None:
                        writer = csv.DictWriter(buf, fieldnames=list(d.keys()))
                        writer.writeheader()
                    writer.writerow(d)
                    yield buf.getvalue().encode()
                    buf.seek(0)
                    buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historico.csv"},
    )
