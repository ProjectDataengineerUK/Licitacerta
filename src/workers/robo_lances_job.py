"""Robô de lances — estratégias de decremento automático.

run() is intentionally NotImplemented until Terms-of-Service review for
browser automation clears legal sign-off.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from src.schemas.robo import ConfiguracaoRobo, EstrategiaLance

logger = logging.getLogger(__name__)


def _calcular_proximo_lance(
    config: ConfiguracaoRobo,
    melhor_valor: Decimal,
    posicao_atual: int,
) -> Decimal | None:
    """Return next lance value, or None if floor reached / already at target."""
    decremento = melhor_valor * Decimal(str(config.decremento_pct)) / Decimal("100")

    if config.estrategia == EstrategiaLance.POR_POSICAO:
        if posicao_atual <= config.posicao_alvo:
            return None
        novo = melhor_valor - decremento
        return novo if novo >= config.valor_floor_brl else None

    if config.estrategia == EstrategiaLance.POR_MARGEM:
        novo = melhor_valor - decremento
        if novo < config.valor_floor_brl:
            return None
        margem_pct = float((novo - config.valor_floor_brl) / config.valor_floor_brl * 100)
        return novo if margem_pct >= config.margem_minima_pct else None

    # EstrategiaLance.POR_VALOR: decrement unconditionally until floor
    novo = melhor_valor - decremento
    return novo if novo >= config.valor_floor_brl else None


async def run(config: ConfiguracaoRobo) -> None:  # noqa: ARG001
    raise NotImplementedError("ToS review pending — browser automation not activated")
