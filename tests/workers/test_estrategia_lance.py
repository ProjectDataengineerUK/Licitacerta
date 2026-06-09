"""Tests for robo_lances_job._calcular_proximo_lance — AT-005, AT-006."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.schemas.robo import ConfiguracaoRobo, EstrategiaLance
from src.workers.robo_lances_job import _calcular_proximo_lance


def _cfg(estrategia: EstrategiaLance, floor: Decimal, **kwargs) -> ConfiguracaoRobo:
    return ConfiguracaoRobo(
        run_id="00000000-0000-0000-0000-000000000001",
        tenant_id="00000000-0000-0000-0000-000000000002",
        estrategia=estrategia,
        valor_floor_brl=floor,
        **kwargs,
    )


# AT-001: POR_POSICAO → already at target → None
def test_at001_por_posicao_ja_na_posicao():
    cfg = _cfg(EstrategiaLance.POR_POSICAO, Decimal("90000"), posicao_alvo=1, decremento_pct=0.5)
    assert _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=1) is None


# AT-002: POR_POSICAO → not at target → decrement
def test_at002_por_posicao_decrementa():
    cfg = _cfg(EstrategiaLance.POR_POSICAO, Decimal("90000"), posicao_alvo=1, decremento_pct=0.5)
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=3)
    assert result == Decimal("99500.00") or result == Decimal("99500")


# AT-003: POR_VALOR → always decrement until floor
def test_at003_por_valor_decrementa():
    cfg = _cfg(EstrategiaLance.POR_VALOR, Decimal("90000"), decremento_pct=1.0)
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=5)
    assert result == Decimal("99000")


# AT-004: POR_VALOR → below floor → None
def test_at004_por_valor_floor_none():
    cfg = _cfg(EstrategiaLance.POR_VALOR, Decimal("99500"), decremento_pct=1.0)
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=5)
    # 100000 - 1000 = 99000 < 99500 floor → None
    assert result is None


# AT-005: POR_POSICAO → decrement lands below floor → None
def test_at005_posicao_floor_check():
    cfg = _cfg(EstrategiaLance.POR_POSICAO, Decimal("99500"), posicao_alvo=1, decremento_pct=1.0)
    # 100000 - 1000 = 99000 < floor 99500
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=2)
    assert result is None


# AT-006: POR_MARGEM → margem below minima → None
def test_at006_margem_minima_triggered():
    # floor=95000, decremento=1%, valor=100000 → novo=99000, margem=(99000-95000)/95000*100 ≈ 4.2% < 5% → None
    cfg = _cfg(EstrategiaLance.POR_MARGEM, Decimal("95000"), margem_minima_pct=5.0, decremento_pct=1.0)
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=2)
    assert result is None


# AT-007: POR_MARGEM → margem above minima → returns value
def test_at007_margem_ok():
    # floor=80000, valor=100000, decremento=1% → novo=99000, margem=(99000-80000)/80000*100 = 23.75% > 5%
    cfg = _cfg(EstrategiaLance.POR_MARGEM, Decimal("80000"), margem_minima_pct=5.0, decremento_pct=1.0)
    result = _calcular_proximo_lance(cfg, Decimal("100000"), posicao_atual=2)
    assert result == Decimal("99000")


# AT-008: run() raises NotImplementedError
def test_at008_run_raises():
    from src.workers.robo_lances_job import run
    from src.schemas.robo import ConfiguracaoRobo, EstrategiaLance
    import asyncio

    cfg = _cfg(EstrategiaLance.POR_VALOR, Decimal("1000"))
    with pytest.raises(NotImplementedError, match="ToS review pending"):
        asyncio.get_event_loop().run_until_complete(run(cfg))
