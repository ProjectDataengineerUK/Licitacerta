from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.auth import require_auth
from src.schemas.market import CompetitorProfile, OrganScore, PriceBenchmark
from src.schemas.pregoeiro import PregoeiroPerfil
from src.services.pregoeiro_service import PregoeicoService

router = APIRouter(prefix="/market", tags=["market-intel"])


def _get_service(request: Request):
    svc = getattr(request.app.state, "market_intel_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="MarketIntelService não disponível")
    return svc


@router.get("/competitor/{cnpj}", response_model=CompetitorProfile)
async def get_competitor_xray(
    cnpj: str,
    _: dict = Depends(require_auth),
    request: Request = None,
):
    svc = _get_service(request)
    try:
        return await svc.competitor_xray(cnpj)
    except Exception:
        return CompetitorProfile(
            cnpj=cnpj,
            taxa_vitoria_pct=0.0,
            total_vitorias=0,
            data_insuficiente=True,
        )


@router.get("/prices", response_model=PriceBenchmark)
async def get_price_benchmark(
    item: str = Query(..., description="Descrição do item"),
    catmat: str | None = Query(None, description="Código CATMAT"),
    orgao: str | None = Query(None, description="CNPJ do órgão"),
    _: dict = Depends(require_auth),
    request: Request = None,
):
    svc = _get_service(request)
    try:
        return await svc.price_benchmark(item, catmat, orgao)
    except Exception:
        return PriceBenchmark(item_descricao=item, amostra=0, data_insuficiente=True)


@router.get("/organ/{uasg}/score", response_model=OrganScore)
async def get_organ_score(
    uasg: str,
    _: dict = Depends(require_auth),
    request: Request = None,
):
    svc = _get_service(request)
    try:
        return await svc.organ_score(uasg=uasg)
    except Exception:
        return OrganScore(
            uasg=uasg,
            orgao_cnpj="",
            score=50,
            label="Regular",
            amostra=0,
            data_insuficiente=True,
        )


@router.get("/pregoeiro", response_model=PregoeiroPerfil)
async def get_pregoeiro_profile(
    nome: str = Query(..., description="Nome do pregoeiro"),
    orgao: str = Query(..., description="CNPJ do órgão"),
    _: dict = Depends(require_auth),
    request: Request = None,
):
    db = getattr(getattr(request, "app", None), "state", None)
    pool = getattr(db, "_mi_pool", None) if db else None
    if pool is None:
        return PregoeiroPerfil(nome=nome, orgao_cnpj=orgao, label_confianca="Sem dados")
    async with pool.acquire() as conn:
        svc = PregoeicoService(conn)
        try:
            return await svc.lookup(nome=nome, orgao_cnpj=orgao)
        except Exception:
            return PregoeiroPerfil(nome=nome, orgao_cnpj=orgao, label_confianca="Sem dados")


@router.get("/summary", response_model=dict)
async def get_segment_summary(
    segmento: str = Query(..., description="Código CNAE"),
    _: dict = Depends(require_auth),
    request: Request = None,
):
    svc = _get_service(request)
    try:
        return await svc.segment_summary(segmento)
    except Exception:
        return {
            "segmento_cnae": segmento,
            "top_fornecedores": [],
            "concentracao_alta": False,
            "cnpj_dominante": None,
        }
