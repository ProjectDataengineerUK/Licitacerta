"""Portfolio optimizer endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.auth import require_role
from src.schemas.portfolio import PortfolioOtimizacaoInput, PortfolioOtimizacaoResult

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/otimizar", response_model=PortfolioOtimizacaoResult)
async def otimizar_portfolio(
    body: PortfolioOtimizacaoInput,
    _auth=Depends(require_role("user", "operator")),
) -> PortfolioOtimizacaoResult:
    from src.services.portfolio_optimizer import otimizar
    return otimizar(body)
